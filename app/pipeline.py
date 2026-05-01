from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any
import logging
import os

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


@dataclass
class _SumRunState:
    """Per-source mutable counters for the SummarizationRun bookkeeping."""
    papers_processed: int = 0
    insights_generated: int = 0
    failures: int = 0


def _ingest_one_paper(
    *,
    db: Database,
    record: PaperRecord,
    summarizer: SummarizationService,
    summary: PipelineSummary,
    force_resummarize: bool,
    sum_state: _SumRunState,
) -> bool:
    """Run normalize -> upsert -> insight for a single record. Returns True
    if the upsert created a new paper. Tags any raised exception with the
    phase name (`_paperclaw_phase` attribute) so the caller can record the
    failure with the right `error_phase`."""
    try:
        normalized = normalize_paper(record)
    except Exception as exc:
        exc._paperclaw_phase = "normalize"  # type: ignore[attr-defined]
        raise

    try:
        result = db.upsert_paper_with_status(normalized)
    except Exception as exc:
        exc._paperclaw_phase = "upsert"  # type: ignore[attr-defined]
        raise

    if result.created:
        summary.new_papers.append(normalized)

    # Insight generation has its own try: a failed insight does NOT push the
    # paper into the failure queue (the paper itself is already stored).
    try:
        existing = db.get_paper_insight(paper_id=result.paper.paper_id)
        needs_insight = (
            force_resummarize
            or existing is None
            or bool(getattr(existing, "is_placeholder", True))
        )
        if needs_insight:
            insight = summarizer.generate(normalized)
            db.upsert_paper_insight(paper_id=result.paper.paper_id, insight=insight)
            summary.total_insighted += 1
            sum_state.insights_generated += 1
    except Exception as insight_exc:
        LOGGER.warning("  论文总结失败 [%s]: %s", normalized.title, insight_exc)
        sum_state.failures += 1
    finally:
        sum_state.papers_processed += 1

    return result.created


def _retry_pending_failures(
    *,
    db: Database,
    source_name: str,
    summarizer: SummarizationService,
    summary: PipelineSummary,
    force_resummarize: bool,
    max_retry: int,
    max_attempts: int,
    sum_state: _SumRunState,
) -> tuple[int, int]:
    """Replay up to `max_retry` pending failures for this source. Returns
    (newly_inserted_count, still_failing_count)."""
    pending = db.list_pending_failures(
        source=source_name,
        limit=max_retry,
        max_attempts=max_attempts,
    )
    if not pending:
        return (0, 0)

    LOGGER.info(f"  从失败队列重放 {len(pending)} 篇待重试论文…")
    new_count = 0
    failed_again = 0
    for failure in pending:
        try:
            record = PaperRecord.model_validate(failure.raw_payload)
        except Exception as deser_exc:
            LOGGER.warning(
                "  重试反序列化失败 (failure_id=%s): %s",
                failure.failure_id, deser_exc,
            )
            db.bump_failure_attempts(
                failure.failure_id,
                error_phase="deserialise",
                error=deser_exc,
            )
            failed_again += 1
            continue

        try:
            created = _ingest_one_paper(
                db=db,
                record=record,
                summarizer=summarizer,
                summary=summary,
                force_resummarize=force_resummarize,
                sum_state=sum_state,
            )
        except Exception as exc:
            phase = getattr(exc, "_paperclaw_phase", "unknown")
            db.bump_failure_attempts(failure.failure_id, error_phase=phase, error=exc)
            LOGGER.warning(
                "  重试仍失败 (failure_id=%s, attempts=%s): %s",
                failure.failure_id, failure.attempts + 1, exc,
            )
            failed_again += 1
            continue

        db.mark_failure_resolved(failure.failure_id)
        if created:
            summary.total_new += 1
            new_count += 1
            LOGGER.info(
                "  ✓ 重试成功并入库 [%s/%s]",
                record.source, record.source_paper_id,
            )

    return (new_count, failed_again)


def run_pipeline(
    database_url: str,
    sources: list,
    notifier=None,
    summarizer: SummarizationService | None = None,
    *,
    force_resummarize: bool = False,
) -> PipelineSummary:
    """运行完整的爬虫管道：抓取 -> 标准化 -> 去重入库 -> 通知。

    若某篇论文已存在非占位 insight，默认跳过 summarization 以保证幂等
    （切到真实 LLM 后这一点会显著节省成本）。传 ``force_resummarize=True``
    可强制重新生成，用于模型升级后回填。

    错误隔离粒度：source.fetch() 整体失败 -> CrawlRun=failed；单篇论文
    在 normalize/upsert/insight 任一步炸 -> 写入 paper_fetch_failures
    继续循环，CrawlRun 仍然 success。下一次 run_pipeline 在 fetch 之前
    先重放最多 PAPER_FETCH_MAX_RETRY_PER_RUN 篇待重试论文，连续失败
    PAPER_FETCH_MAX_RETRY_ATTEMPTS 次后停止自动重试。
    """
    LOGGER.info(f"正在连接到数据库：{database_url}")
    db = Database(database_url)
    db.create_schema()
    LOGGER.info("数据库 schema 已创建/验证")

    summary = PipelineSummary()
    summarizer = summarizer or SummarizationService()

    # Track summarization run
    sum_run = db.start_summarization_run()
    sum_state = _SumRunState()

    LOGGER.info(f"开始处理 {len(sources)} 个数据源...")

    max_retry_per_run = int(os.environ.get("PAPER_FETCH_MAX_RETRY_PER_RUN", "50"))
    max_retry_attempts = int(os.environ.get("PAPER_FETCH_MAX_RETRY_ATTEMPTS", "5"))

    for source in sources:
        source_name = getattr(source, "name", source.__class__.__name__.lower())
        LOGGER.info(f"「数据源 [{source_name}]」开始处理...")

        crawl_run = db.start_crawl_run(source_name)
        fetched_count = 0
        new_count = 0
        failed_papers = 0

        # First: replay any pending failures from prior runs. Their successful
        # inserts count as new_count (the paper is genuinely new to `papers`)
        # but they do NOT count as fetched_count — fetched_count tracks what
        # this run's source.fetch() returned.
        retry_new, retry_failed = _retry_pending_failures(
            db=db,
            source_name=source_name,
            summarizer=summarizer,
            summary=summary,
            force_resummarize=force_resummarize,
            max_retry=max_retry_per_run,
            max_attempts=max_retry_attempts,
            sum_state=sum_state,
        )
        new_count += retry_new
        failed_papers += retry_failed

        try:
            LOGGER.info(f"  正在从 {source_name} 抓取论文...")
            fetched_records = source.fetch()
        except Exception as exc:
            # Only the source-level fetch failure flips the CrawlRun to
            # failed. Per-paper failures below do not.
            LOGGER.exception(f"  ✗ {source_name} fetch 阶段失败")
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
                "failed_papers": failed_papers,
                "error": str(exc),
            }
            summary.failed_sources.append(source_name)
            continue

        fetched_count = len(fetched_records)
        summary.total_fetched += fetched_count
        LOGGER.info(f"  成功抓取 {fetched_count} 条记录")
        if fetched_count == 0:
            LOGGER.warning(f"  警告：{source_name} 返回 0 条记录")

        for i, record in enumerate(fetched_records, 1):
            try:
                created = _ingest_one_paper(
                    db=db,
                    record=record,
                    summarizer=summarizer,
                    summary=summary,
                    force_resummarize=force_resummarize,
                    sum_state=sum_state,
                )
            except Exception as per_paper_exc:
                LOGGER.warning(
                    "  [%s/%s] %s -> 失败：%s（已写入失败队列，下次重试）",
                    i, fetched_count, record.title, per_paper_exc,
                )
                phase = getattr(per_paper_exc, "_paperclaw_phase", "unknown")
                db.record_paper_failure(
                    source=source_name,
                    record=record,
                    error_phase=phase,
                    error=per_paper_exc,
                )
                failed_papers += 1
                continue

            LOGGER.info(
                "  [%s/%s] %s -> %s",
                i, fetched_count, record.title,
                "新增入库" if created else "已存在，跳过新增",
            )
            if created:
                summary.total_new += 1
                new_count += 1

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
            "failed_papers": failed_papers,
        }
        LOGGER.info(
            f"  ✓ {source_name} 处理完成：抓 {fetched_count} 条，"
            f"新增 {new_count} 条，失败入队 {failed_papers} 条"
        )

    LOGGER.info(f"所有数据源处理完成：总计获取 {summary.total_fetched} 条，新增 {summary.total_new} 篇论文")
    if summary.failed_sources:
        LOGGER.warning("以下数据源处理失败：%s", summary.failed_sources)

    has_sum_failure = bool(summary.failed_sources) or sum_state.failures > 0
    error_parts = []
    if summary.failed_sources:
        error_parts.append(f"Source failures: {', '.join(summary.failed_sources)}")
    if sum_state.failures > 0:
        error_parts.append(f"{sum_state.failures} paper summarization(s) failed")
    db.finish_summarization_run(
        sum_run.run_id,
        status="failed" if has_sum_failure else "success",
        papers_processed=sum_state.papers_processed,
        insights_generated=sum_state.insights_generated,
        error_message="; ".join(error_parts) if error_parts else None,
    )

    if summary.new_papers:
        LOGGER.info("抓取流程结束，本轮新增待发送论文 %s 篇", len(summary.new_papers))
        for paper in summary.new_papers:
            LOGGER.info("待发送论文：%s", paper.title)
    else:
        LOGGER.info("抓取流程结束，本轮没有新增待发送论文")

    return summary
