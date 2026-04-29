from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base, CrawlRun, EditorialDraft, EditorialRun, ExportRecord, Notification, Paper, PaperInsight, PaperVersion, SummarizationRun
from app.schemas import PaperRecord
from app.summarization.schemas import PaperInsightRecord
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

    def upsert_paper_insight(self, *, paper_id: int, insight: PaperInsightRecord) -> PaperInsight:
        with self._session() as session:
            paper = session.get(Paper, paper_id)
            if paper is None:
                raise ValueError(f"paper {paper_id} does not exist")

            stored = session.scalar(select(PaperInsight).where(PaperInsight.paper_id == paper_id))
            if stored is None:
                stored = PaperInsight(paper_id=paper_id)
                session.add(stored)

            stored.summary_short = insight.summary_short
            stored.summary_long = insight.summary_long
            stored.novelty_points = list(insight.novelty_points)
            stored.limitations = list(insight.limitations)
            stored.applications = list(insight.applications)
            stored.confidence_score = insight.confidence_score

            session.commit()
            return stored

    def get_paper_insight(self, *, paper_id: int) -> PaperInsight | None:
        with self._session() as session:
            return session.scalar(select(PaperInsight).where(PaperInsight.paper_id == paper_id))

    def list_unnotified_papers_with_limit(self, *, destination: str, limit: int) -> list[Paper]:
        return self.list_unnotified_papers(destination=destination, limit=limit)

    def list_papers_with_insights(self, *, limit: int) -> list[tuple[Paper, PaperInsight]]:
        stmt = (
            select(Paper, PaperInsight)
            .join(PaperInsight, Paper.paper_id == PaperInsight.paper_id)
            .order_by(Paper.paper_id.desc())
            .limit(limit)
        )
        with self._session() as session:
            rows = session.execute(stmt).all()
            return [(paper, insight) for paper, insight in rows]

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

    def upsert_editorial_draft(
        self,
        *,
        paper_id: int,
        platform: str,
        title: str,
        hook: str,
        markdown_content: str,
        output_path: str,
    ) -> EditorialDraft:
        with self._session() as session:
            draft = session.scalar(
                select(EditorialDraft).where(
                    EditorialDraft.paper_id == paper_id,
                    EditorialDraft.platform == platform,
                )
            )
            if draft is None:
                draft = EditorialDraft(
                    draft_id=f"draft-{uuid4().hex}",
                    paper_id=paper_id,
                    platform=platform,
                )
                session.add(draft)

            draft.title = title
            draft.hook = hook
            draft.markdown_content = markdown_content
            draft.output_path = output_path
            draft.status = "generated"
            draft.review_note = None
            draft.reviewed_by = None
            draft.reviewed_at = None
            draft.approved_by = None
            draft.approved_at = None
            draft.rejected_by = None
            draft.rejected_at = None
            draft.exported_at = None
            session.commit()
            return draft

    def list_editorial_drafts(self, *, platform: str | None = None, status: str | None = None) -> list[EditorialDraft]:
        stmt = select(EditorialDraft).order_by(EditorialDraft.created_at.asc())
        if platform is not None:
            stmt = stmt.where(EditorialDraft.platform == platform)
        if status is not None:
            stmt = stmt.where(EditorialDraft.status == status)
        with self._session() as session:
            return list(session.scalars(stmt))

    def get_editorial_draft(self, draft_id: str) -> EditorialDraft | None:
        with self._session() as session:
            return session.get(EditorialDraft, draft_id)

    def assign_editorial_draft(self, draft_id: str, *, assignee: str, actor: str | None = None) -> EditorialDraft:
        with self._session() as session:
            draft = self._require_draft(session, draft_id)
            draft.assignee = assignee
            if actor:
                draft.review_note = f"assigned by {actor}"
            session.commit()
            return draft

    def review_editorial_draft(self, draft_id: str, *, actor: str, note: str | None = None) -> EditorialDraft:
        with self._session() as session:
            draft = self._require_draft(session, draft_id)
            self._transition_draft(draft, target_status="in_review")
            draft.reviewed_by = actor
            draft.reviewed_at = utc_now()
            draft.review_note = note
            session.commit()
            return draft

    def approve_editorial_draft(self, draft_id: str, *, actor: str, note: str | None = None) -> EditorialDraft:
        with self._session() as session:
            draft = self._require_draft(session, draft_id)
            self._transition_draft(draft, target_status="approved")
            draft.approved_by = actor
            draft.approved_at = utc_now()
            draft.review_note = note
            session.commit()
            return draft

    def reject_editorial_draft(self, draft_id: str, *, actor: str, note: str | None = None) -> EditorialDraft:
        with self._session() as session:
            draft = self._require_draft(session, draft_id)
            self._transition_draft(draft, target_status="rejected")
            draft.rejected_by = actor
            draft.rejected_at = utc_now()
            draft.review_note = note
            session.commit()
            return draft

    def record_export_success(
        self,
        *,
        draft_id: str,
        exported_by: str,
        source_path: str,
        destination_path: str,
    ) -> ExportRecord:
        with self._session() as session:
            draft = self._require_draft(session, draft_id)
            self._transition_draft(draft, target_status="exported")
            draft.exported_at = utc_now()
            record = ExportRecord(
                draft_id=draft_id,
                exported_by=exported_by,
                success=True,
                source_path=source_path,
                destination_path=destination_path,
            )
            session.add(record)
            session.commit()
            return record

    def record_export_failure(
        self,
        *,
        draft_id: str,
        exported_by: str,
        source_path: str,
        error_message: str,
    ) -> ExportRecord:
        with self._session() as session:
            self._require_draft(session, draft_id)
            record = ExportRecord(
                draft_id=draft_id,
                exported_by=exported_by,
                success=False,
                source_path=source_path,
                destination_path=None,
                error_message=error_message,
            )
            session.add(record)
            session.commit()
            return record

    def list_export_records(self) -> list[ExportRecord]:
        with self._session() as session:
            return list(session.scalars(select(ExportRecord).order_by(ExportRecord.export_id.asc())))

    def count_papers(self) -> int:
        with self._session() as session:
            return session.scalar(select(func.count()).select_from(Paper)) or 0

    def list_crawl_runs(self, *, source: str | None = None, limit: int = 50) -> list[CrawlRun]:
        stmt = select(CrawlRun).order_by(CrawlRun.run_id.desc())
        if source is not None:
            stmt = stmt.where(CrawlRun.source == source)
        stmt = stmt.limit(limit)
        with self._session() as session:
            return list(session.scalars(stmt).all())

    def start_summarization_run(self) -> SummarizationRun:
        run = SummarizationRun(status="running")
        with self._session() as session:
            session.add(run)
            session.commit()
            return run

    def finish_summarization_run(
        self,
        run_id: int,
        *,
        status: str,
        papers_processed: int = 0,
        insights_generated: int = 0,
        error_message: str | None = None,
    ) -> SummarizationRun:
        with self._session() as session:
            run = session.get(SummarizationRun, run_id)
            if run is None:
                raise ValueError(f"summarization run {run_id} does not exist")
            run.status = status
            run.papers_processed = papers_processed
            run.insights_generated = insights_generated
            run.error_message = error_message
            run.finished_at = run.finished_at or utc_now()
            session.commit()
            return run

    def list_summarization_runs(self, *, limit: int = 50) -> list[SummarizationRun]:
        stmt = select(SummarizationRun).order_by(SummarizationRun.run_id.desc()).limit(limit)
        with self._session() as session:
            return list(session.scalars(stmt).all())

    def start_editorial_run(self) -> EditorialRun:
        run = EditorialRun(status="running")
        with self._session() as session:
            session.add(run)
            session.commit()
            return run

    def finish_editorial_run(
        self,
        run_id: int,
        *,
        status: str,
        papers_processed: int = 0,
        drafts_generated: int = 0,
        error_message: str | None = None,
    ) -> EditorialRun:
        with self._session() as session:
            run = session.get(EditorialRun, run_id)
            if run is None:
                raise ValueError(f"editorial run {run_id} does not exist")
            run.status = status
            run.papers_processed = papers_processed
            run.drafts_generated = drafts_generated
            run.error_message = error_message
            run.finished_at = run.finished_at or utc_now()
            session.commit()
            return run

    def list_editorial_runs(self, *, limit: int = 50) -> list[EditorialRun]:
        stmt = select(EditorialRun).order_by(EditorialRun.run_id.desc()).limit(limit)
        with self._session() as session:
            return list(session.scalars(stmt).all())

    def _session(self) -> Session:
        return self._session_factory()

    def _migrate_sqlite_schema(self) -> None:
        if self.engine.dialect.name != "sqlite":
            return

        inspector = inspect(self.engine)
        statements: list[str] = []

        if inspector.has_table("notifications"):
            notification_columns = {column["name"] for column in inspector.get_columns("notifications")}
            if "success" not in notification_columns:
                statements.append("ALTER TABLE notifications ADD COLUMN success BOOLEAN NOT NULL DEFAULT 1")
            if "error_message" not in notification_columns:
                statements.append("ALTER TABLE notifications ADD COLUMN error_message TEXT")

        if inspector.has_table("papers"):
            paper_columns = {column["name"] for column in inspector.get_columns("papers")}
            if "full_text" not in paper_columns:
                statements.append("ALTER TABLE papers ADD COLUMN full_text TEXT")

        if inspector.has_table("paper_versions"):
            version_columns = {column["name"] for column in inspector.get_columns("paper_versions")}
            if "full_text" not in version_columns:
                statements.append("ALTER TABLE paper_versions ADD COLUMN full_text TEXT")

        if inspector.has_table("editorial_drafts"):
            editorial_columns = {column["name"] for column in inspector.get_columns("editorial_drafts")}
            for statement in self._editorial_draft_migration_statements(editorial_columns):
                statements.append(statement)

        if inspector.has_table("export_records"):
            export_columns = {column["name"] for column in inspector.get_columns("export_records")}
            if "success" not in export_columns:
                statements.append("ALTER TABLE export_records ADD COLUMN success BOOLEAN NOT NULL DEFAULT 1")
            if "destination_path" not in export_columns:
                statements.append("ALTER TABLE export_records ADD COLUMN destination_path VARCHAR(1000)")
            if "error_message" not in export_columns:
                statements.append("ALTER TABLE export_records ADD COLUMN error_message TEXT")

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
        paper.full_text = record.full_text
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
            full_text=paper.full_text,
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

    @staticmethod
    def _require_draft(session: Session, draft_id: str) -> EditorialDraft:
        draft = session.get(EditorialDraft, draft_id)
        if draft is None:
            raise ValueError(f"editorial draft {draft_id} does not exist")
        return draft

    @staticmethod
    def _transition_draft(draft: EditorialDraft, *, target_status: str) -> None:
        allowed = {
            "generated": {"in_review"},
            "in_review": {"approved", "rejected"},
            "approved": {"exported"},
            "rejected": {"in_review"},
            "exported": set(),
        }
        current = draft.status
        if target_status not in allowed.get(current, set()):
            raise ValueError(f"illegal transition: {current} -> {target_status}")
        draft.status = target_status

    @staticmethod
    def _editorial_draft_migration_statements(columns: set[str]) -> list[str]:
        statements: list[str] = []
        desired_columns = {
            "markdown_content": "ALTER TABLE editorial_drafts ADD COLUMN markdown_content TEXT NOT NULL DEFAULT ''",
            "assignee": "ALTER TABLE editorial_drafts ADD COLUMN assignee VARCHAR(255)",
            "review_note": "ALTER TABLE editorial_drafts ADD COLUMN review_note TEXT",
            "reviewed_by": "ALTER TABLE editorial_drafts ADD COLUMN reviewed_by VARCHAR(255)",
            "reviewed_at": "ALTER TABLE editorial_drafts ADD COLUMN reviewed_at DATETIME",
            "approved_by": "ALTER TABLE editorial_drafts ADD COLUMN approved_by VARCHAR(255)",
            "approved_at": "ALTER TABLE editorial_drafts ADD COLUMN approved_at DATETIME",
            "rejected_by": "ALTER TABLE editorial_drafts ADD COLUMN rejected_by VARCHAR(255)",
            "rejected_at": "ALTER TABLE editorial_drafts ADD COLUMN rejected_at DATETIME",
            "exported_at": "ALTER TABLE editorial_drafts ADD COLUMN exported_at DATETIME",
        }
        for column, statement in desired_columns.items():
            if column not in columns:
                statements.append(statement)
        return statements
