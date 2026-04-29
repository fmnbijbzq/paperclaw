from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any
import logging

from app.normalizer import normalize_paper
from app.schemas import PaperRecord
from app.storage import Database
from app.summarization.service import SummarizationService

LOGGER = logging.getLogger(__name__)


@dataclass
class PipelineSummary:
    total_fetched: int = 0
    total_new: int = 0
    total_notified: int = 0
    total_insighted: int = 0
    new_papers: list[PaperRecord] = field(default_factory=list)
    per_source: dict[str, dict[str, Any]] = field(default_factory=dict)
    failed_sources: list[str] = field(default_factory=list)

    @property
    def has_failures(self) -> bool:
        return bool(self.failed_sources)


def run_pipeline(database_url: str, sources: list, notifier=None, summarizer: SummarizationService | None = None) -> PipelineSummary:
    """运行完整的爬虫管道：抓取 -> 标准化 -> 去重入库 -> 通知。"""
    LOGGER.info(f"正在连接到数据库：{database_url}")
    db = Database(database_url)
    db.create_schema()
    LOGGER.info("数据库 schema 已创建/验证")

    summary = PipelineSummary()
    summarizer = summarizer or SummarizationService()

    # Track summarization run
    sum_run = db.start_summarization_run()
    sum_papers_processed = 0
    sum_insights_generated = 0
    sum_failures = 0

    # 统计启用的数据源数量
    LOGGER.info(f"开始处理 {len(sources)} 个数据源...")

    for source in sources:
        source_name = getattr(source, "name", source.__class__.__name__.lower())
        LOGGER.info(f"「数据源 [{source_name}]」开始处理...")

        crawl_run = db.start_crawl_run(source_name)
        fetched_count = 0
        new_count = 0

        try:
            LOGGER.info(f"  正在从 {source_name} 抓取论文...")
            fetched_records = source.fetch()
            fetched_count = len(fetched_records)
            summary.total_fetched += fetched_count
            LOGGER.info(f"  成功抓取 {fetched_count} 条记录")

            if fetched_count == 0:
                LOGGER.warning(f"  警告：{source_name} 返回 0 条记录，可能是配置问题或来源无新论文")

            # 标准化并入库
            LOGGER.info(f"  正在处理 {fetched_count} 条记录的标准化和入库...")
            for i, record in enumerate(fetched_records, 1):
                normalized = normalize_paper(record)
                result = db.upsert_paper_with_status(normalized)
                LOGGER.info(
                    "  [%s/%s] %s -> %s",
                    i,
                    fetched_count,
                    normalized.title,
                    "新增入库" if result.created else "已存在，跳过新增",
                )
                if result.created:
                    summary.total_new += 1
                    new_count += 1
                    summary.new_papers.append(normalized)

                try:
                    insight = summarizer.generate(normalized)
                    db.upsert_paper_insight(paper_id=result.paper.paper_id, insight=insight)
                    summary.total_insighted += 1
                    sum_insights_generated += 1
                except Exception as insight_exc:
                    LOGGER.warning("  论文总结失败 [%s]: %s", normalized.title, insight_exc)
                    sum_failures += 1
                finally:
                    sum_papers_processed += 1

            # 完成当前数据源的抓取任务
            db.finish_crawl_run(
                crawl_run.run_id,
                status="success",
                fetched_count=fetched_count,
                new_count=new_count,
            )
            summary.per_source[source_name] = {
                "status": "success",
                "fetched": fetched_count,
                "new": new_count,
            }
            LOGGER.info(f"  ✓ {source_name} 处理完成：抓 _{fetched_count} 条，新增 {new_count} 条")

        except Exception as exc:
            LOGGER.exception(f"  ✗ {source_name} 处理失败！")
            db.finish_crawl_run(
                crawl_run.run_id,
                status="failed",
                fetched_count=fetched_count,
                new_count=new_count,
                error_message=str(exc),
            )
            summary.per_source[source_name] = {
                "status": "failed",
                "fetched": fetched_count,
                "new": new_count,
                "error": str(exc),
            }
            summary.failed_sources.append(source_name)
            continue

    # 总结抓取结果
    LOGGER.info(f"所有数据源处理完成：总计获取 {summary.total_fetched} 条，新增 {summary.total_new} 篇论文")
    if summary.failed_sources:
        LOGGER.warning("以下数据源处理失败：%s", summary.failed_sources)

    # Finish summarization run
    has_sum_failure = bool(summary.failed_sources) or sum_failures > 0
    error_parts = []
    if summary.failed_sources:
        error_parts.append(f"Source failures: {', '.join(summary.failed_sources)}")
    if sum_failures > 0:
        error_parts.append(f"{sum_failures} paper summarization(s) failed")
    db.finish_summarization_run(
        sum_run.run_id,
        status="failed" if has_sum_failure else "success",
        papers_processed=sum_papers_processed,
        insights_generated=sum_insights_generated,
        error_message="; ".join(error_parts) if error_parts else None,
    )

    if summary.new_papers:
        LOGGER.info("抓取流程结束，本轮新增待发送论文 %s 篇", len(summary.new_papers))
        for paper in summary.new_papers:
            LOGGER.info("待发送论文：%s", paper.title)
    else:
        LOGGER.info("抓取流程结束，本轮没有新增待发送论文")

    return summary
