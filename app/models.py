from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.utils.time import utc_now


class Base(DeclarativeBase):
    pass


class Paper(Base):
    __tablename__ = "papers"
    __table_args__ = (UniqueConstraint("source", "source_paper_id", name="uq_papers_source_source_paper_id"),)

    paper_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    source_paper_id: Mapped[str] = mapped_column(String(255), nullable=False)
    dedup_key: Mapped[str | None] = mapped_column(String(500))
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    abstract: Mapped[str | None] = mapped_column(Text)
    full_text: Mapped[str | None] = mapped_column(Text)
    authors: Mapped[list[str]] = mapped_column(JSON, default=list)
    paper_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    pdf_url: Mapped[str | None] = mapped_column(String(1000))
    venue: Mapped[str | None] = mapped_column(String(255))
    categories: Mapped[list[str]] = mapped_column(JSON, default=list)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at_source: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    versions: Mapped[list["PaperVersion"]] = relationship(back_populates="paper", cascade="all, delete-orphan")
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="paper",
        cascade="all, delete-orphan",
    )
    insights: Mapped[list["PaperInsight"]] = relationship(
        back_populates="paper",
        cascade="all, delete-orphan",
    )


class PaperVersion(Base):
    __tablename__ = "paper_versions"

    version_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("papers.paper_id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    abstract: Mapped[str | None] = mapped_column(Text)
    full_text: Mapped[str | None] = mapped_column(Text)
    authors: Mapped[list[str]] = mapped_column(JSON, default=list)
    categories: Mapped[list[str]] = mapped_column(JSON, default=list)
    paper_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    pdf_url: Mapped[str | None] = mapped_column(String(1000))
    venue: Mapped[str | None] = mapped_column(String(255))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at_source: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    paper: Mapped[Paper] = relationship(back_populates="versions")


class CrawlRun(Base):
    __tablename__ = "crawl_runs"

    run_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="running", nullable=False)
    fetched_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Notification(Base):
    __tablename__ = "notifications"

    notification_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    destination: Mapped[str] = mapped_column(String(255), nullable=False)
    paper_id: Mapped[int] = mapped_column(ForeignKey("papers.paper_id", ondelete="CASCADE"), nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

    paper: Mapped[Paper] = relationship(back_populates="notifications")


class PaperInsight(Base):
    __tablename__ = "paper_insights"
    __table_args__ = (UniqueConstraint("paper_id", name="uq_paper_insights_paper_id"),)

    insight_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("papers.paper_id", ondelete="CASCADE"), nullable=False)
    summary_short: Mapped[str] = mapped_column(Text, nullable=False)
    summary_long: Mapped[str] = mapped_column(Text, nullable=False)
    novelty_points: Mapped[list[str]] = mapped_column(JSON, default=list)
    limitations: Mapped[list[str]] = mapped_column(JSON, default=list)
    applications: Mapped[list[str]] = mapped_column(JSON, default=list)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    paper: Mapped[Paper] = relationship(back_populates="insights")
