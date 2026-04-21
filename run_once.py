from __future__ import annotations

from pathlib import Path
import logging

from app.config import AppSettings, load_source_config
from app.logging import configure_logging
from app.pipeline import run_pipeline
from app.sources.arxiv import ArxivSource
from app.sources.openreview import OpenReviewSource

LOGGER = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parent
SOURCE_CONFIG_PATH = PROJECT_ROOT / "config" / "sources.yaml"


def run_pipeline_from_config() -> int:
    """根据配置文件运行主流程。"""
    LOGGER.info("开始初始化 PaperCrawler")
    LOGGER.info("正在加载配置...")
    settings = AppSettings()

    LOGGER.info(f"日志级别：{settings.log_level}")
    LOGGER.info(f"数据库路径：{settings.database_url}")
    LOGGER.info(f"时区：{settings.timezone}")
    LOGGER.info(f"最大通知条目：{settings.max_notify_items}")

    configure_logging(settings)

    LOGGER.info("正在加载数据来源配置...")
    source_config = load_source_config(SOURCE_CONFIG_PATH)

    # 检查配置是否加载成功
    LOGGER.info(f"数据来源配置路径：{SOURCE_CONFIG_PATH}")
    LOGGER.info(f"数据来源配置文件存在：{SOURCE_CONFIG_PATH.exists()}")
    LOGGER.info(f"数据来源配置内容：{source_config}")

    sources = []

    # 初始化 arXiv 源
    arxiv_config = source_config.get("arxiv", {})
    LOGGER.info(f"arXiv 配置：{arxiv_config}")
    if arxiv_config.get("enabled"):
        LOGGER.info("启用 arXiv 数据源")
        arxiv_lookback = arxiv_config.get("lookback_days")
        LOGGER.info(f"  类别：{arxiv_config.get('categories')}")
        LOGGER.info(f"  回溯天数：{arxiv_lookback}")
        sources.append(
            ArxivSource(
                allowed_categories=arxiv_config.get("categories"),
                lookback_days=arxiv_lookback,
            )
        )
        LOGGER.info(f"  arXiv 源初始化完成")
    else:
        LOGGER.info("arXiv 数据源已禁用，跳过")

    # 初始化 OpenReview 源
    openreview_config = source_config.get("openreview", {})
    LOGGER.info(f"OpenReview 配置：{openreview_config}")
    if openreview_config.get("enabled"):
        LOGGER.info("启用 OpenReview 数据源")
        openreview_lookback = openreview_config.get("lookback_days")
        LOGGER.info(f"   Venue: {openreview_config.get('venues')}")
        LOGGER.info(f"  回溯天数：{openreview_lookback}")
        sources.append(
            OpenReviewSource(
                venues=openreview_config.get("venues"),
                lookback_days=openreview_lookback,
            )
        )
        LOGGER.info(f"  OpenReview 源初始化完成")
    else:
        LOGGER.info("OpenReview 数据源已禁用，跳过")

    LOGGER.info(f"初始化完成后，共 {len(sources)} 个数据源：{[s.name for s in sources]}")

    LOGGER.info(f"使用日志级别：{settings.log_level}")
    LOGGER.info("开始执行爬虫管道...")
    LOGGER.debug(f"数据库 URL: {settings.database_url}")
    LOGGER.debug(f"数据源：{sources}")

    summary = run_pipeline(
        database_url=settings.database_url,
        sources=sources,
        notifier=None,
    )

    LOGGER.info(f"爬虫管道执行完成")
    LOGGER.info(f"统计：获取 {summary.total_fetched} 篇，新增 {summary.total_new} 篇，通知 {summary.total_notified} 篇")

    # 输出每个数据源的结果
    for source_name, stats in summary.per_source.items():
        LOGGER.info(f"数据源 [{source_name}]: 状态={stats.get('status')}, 获取={stats.get('fetched')}, 新增={stats.get('new')}")
        if stats.get('error'):
            LOGGER.error(f"  错误信息：{stats.get('error')}")

    return 1 if getattr(summary, "has_failures", False) else 0


def main() -> int:
    try:
        return run_pipeline_from_config()
    except Exception:
        LOGGER.exception("paperclaw run failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
