from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.normalizer import normalize_paper
from app.schemas import PaperRecord
from app.storage import Database


@dataclass
class PipelineSummary:
    total_fetched: int = 0
    total_new: int = 0
    total_notified: int = 0
    new_papers: list[PaperRecord] = field(default_factory=list)
    per_source: dict[str, dict[str, Any]] = field(default_factory=dict)


def run_pipeline(database_url: str, sources: list, notifier=None) -> PipelineSummary:
    db = Database(database_url)
    db.create_schema()
    summary = PipelineSummary()

    for source in sources:
        source_name = getattr(source, "name", source.__class__.__name__.lower())
        crawl_run = db.start_crawl_run(source_name)
        fetched_count = 0
        new_count = 0

        try:
            fetched_records = source.fetch()
            fetched_count = len(fetched_records)
            summary.total_fetched += fetched_count

            for record in fetched_records:
                normalized = normalize_paper(record)
                result = db.upsert_paper_with_status(normalized)
                if result.created:
                    summary.total_new += 1
                    new_count += 1
                    summary.new_papers.append(normalized)

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
        except Exception as exc:
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
            raise

    if notifier is not None and summary.new_papers:
        if hasattr(notifier, "notify"):
            notifier.notify(summary)
        elif callable(notifier):
            notifier(summary)
        summary.total_notified = len(summary.new_papers)

    return summary
