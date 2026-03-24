from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base, CrawlRun, Notification, Paper, PaperVersion
from app.schemas import PaperRecord
from app.utils.time import utc_now


@dataclass
class UpsertPaperResult:
    paper: Paper
    created: bool


class Database:
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url, future=True)
        self._session_factory = sessionmaker(self.engine, expire_on_commit=False)

    def create_schema(self) -> None:
        Base.metadata.create_all(self.engine)

    def table_exists(self, name: str) -> bool:
        return inspect(self.engine).has_table(name)

    def start_crawl_run(self, source: str) -> CrawlRun:
        crawl_run = CrawlRun(source=source, status="running")
        with self._session() as session:
            session.add(crawl_run)
            session.commit()
            return crawl_run

    def finish_crawl_run(
        self,
        run_id: int,
        *,
        status: str,
        fetched_count: int = 0,
        new_count: int = 0,
        error_message: str | None = None,
    ) -> CrawlRun:
        with self._session() as session:
            crawl_run = session.get(CrawlRun, run_id)
            if crawl_run is None:
                raise ValueError(f"crawl run {run_id} does not exist")

            crawl_run.status = status
            crawl_run.fetched_count = fetched_count
            crawl_run.new_count = new_count
            crawl_run.error_message = error_message
            crawl_run.finished_at = crawl_run.finished_at or utc_now()
            session.commit()
            return crawl_run

    def upsert_paper(self, record: PaperRecord) -> Paper:
        return self.upsert_paper_with_status(record).paper

    def upsert_paper_with_status(self, record: PaperRecord) -> UpsertPaperResult:
        with self._session() as session:
            paper = session.scalar(
                select(Paper).where(
                    Paper.source == record.source,
                    Paper.source_paper_id == record.source_paper_id,
                )
            )

            created = paper is None
            if created:
                paper = Paper(source=record.source, source_paper_id=record.source_paper_id)
                session.add(paper)

            assert paper is not None
            self._apply_record(paper, record)

            if created or self._paper_changed(session, paper):
                session.flush()
                session.add(self._build_version(paper))

            session.commit()
            return UpsertPaperResult(paper=paper, created=created)

    def record_notification(self, *, destination: str, papers: Iterable[Paper]) -> list[Notification]:
        notifications: list[Notification] = []
        with self._session() as session:
            for paper in papers:
                notification = Notification(destination=destination, paper_id=paper.paper_id)
                session.add(notification)
                notifications.append(notification)

            session.commit()
            return notifications

    def list_unnotified_papers(self, *, limit: int) -> list[Paper]:
        notified = select(Notification.paper_id)
        stmt = (
            select(Paper)
            .where(~Paper.paper_id.in_(notified))
            .order_by(Paper.paper_id.asc())
            .limit(limit)
        )
        with self._session() as session:
            return list(session.scalars(stmt))

    def count_papers(self) -> int:
        with self._session() as session:
            return session.scalar(select(func.count()).select_from(Paper)) or 0

    def _session(self) -> Session:
        return self._session_factory()

    @staticmethod
    def _apply_record(paper: Paper, record: PaperRecord) -> None:
        paper.dedup_key = record.dedup_key
        paper.title = record.title
        paper.abstract = record.abstract
        paper.authors = list(record.authors)
        paper.paper_url = record.paper_url
        paper.pdf_url = record.pdf_url
        paper.venue = record.venue
        paper.categories = list(record.categories)
        paper.published_at = record.published_at
        paper.updated_at_source = record.updated_at_source
        paper.raw_payload = dict(record.raw_payload)

    @staticmethod
    def _build_version(paper: Paper) -> PaperVersion:
        return PaperVersion(
            paper=paper,
            title=paper.title,
            abstract=paper.abstract,
            authors=list(paper.authors),
            categories=list(paper.categories),
            paper_url=paper.paper_url,
            pdf_url=paper.pdf_url,
            venue=paper.venue,
            published_at=paper.published_at,
            updated_at_source=paper.updated_at_source,
            raw_payload=dict(paper.raw_payload),
        )

    @staticmethod
    def _paper_changed(session: Session, paper: Paper) -> bool:
        return session.is_modified(paper, include_collections=False)
