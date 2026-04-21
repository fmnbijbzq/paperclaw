from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.engine import make_url
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
        self._ensure_sqlite_parent_dir(database_url)
        self.engine = create_engine(database_url, future=True)
        self._session_factory = sessionmaker(self.engine, expire_on_commit=False)

    def create_schema(self) -> None:
        Base.metadata.create_all(self.engine)
        self._migrate_sqlite_schema()

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

    def record_notification_attempt(
        self,
        *,
        destination: str,
        paper: Paper,
        success: bool,
        error_message: str | None = None,
    ) -> Notification:
        with self._session() as session:
            notification = Notification(
                destination=destination,
                paper_id=paper.paper_id,
                success=success,
                error_message=error_message,
            )
            session.add(notification)
            session.commit()
            return notification

    def record_notifications(
        self,
        *,
        destination: str,
        papers: Iterable[Paper],
        success: bool,
        error_message: str | None = None,
    ) -> list[Notification]:
        notifications: list[Notification] = []
        with self._session() as session:
            for paper in papers:
                notification = Notification(
                    destination=destination,
                    paper_id=paper.paper_id,
                    success=success,
                    error_message=error_message,
                )
                session.add(notification)
                notifications.append(notification)

            session.commit()
            return notifications

    def list_unnotified_papers(self, *, destination: str, limit: int) -> list[Paper]:
        notified = select(Notification.paper_id).where(
            Notification.destination == destination,
            Notification.success.is_(True),
        )
        stmt = (
            select(Paper)
            .where(~Paper.paper_id.in_(notified))
            .order_by(Paper.paper_id.asc())
            .limit(limit)
        )
        with self._session() as session:
            return list(session.scalars(stmt))

    def list_notifications(self, *, destination: str) -> list[Notification]:
        stmt = (
            select(Notification)
            .where(Notification.destination == destination)
            .order_by(Notification.notification_id.asc())
        )
        with self._session() as session:
            return list(session.scalars(stmt))

    def count_papers(self) -> int:
        with self._session() as session:
            return session.scalar(select(func.count()).select_from(Paper)) or 0

    def _session(self) -> Session:
        return self._session_factory()

    def _migrate_sqlite_schema(self) -> None:
        if self.engine.dialect.name != "sqlite":
            return

        inspector = inspect(self.engine)
        if not inspector.has_table("notifications"):
            return

        columns = {column["name"] for column in inspector.get_columns("notifications")}
        statements: list[str] = []
        if "success" not in columns:
            statements.append("ALTER TABLE notifications ADD COLUMN success BOOLEAN NOT NULL DEFAULT 1")
        if "error_message" not in columns:
            statements.append("ALTER TABLE notifications ADD COLUMN error_message TEXT")

        if not statements:
            return

        with self.engine.begin() as connection:
            for statement in statements:
                connection.execute(text(statement))

    @staticmethod
    def _ensure_sqlite_parent_dir(database_url: str) -> None:
        url = make_url(database_url)
        if url.drivername != "sqlite":
            return

        database = url.database
        if not database or database == ":memory:":
            return

        Path(database).parent.mkdir(parents=True, exist_ok=True)

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
