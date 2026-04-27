from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PaperRecord(BaseModel):
    source: str
    source_paper_id: str
    dedup_key: str | None = None
    title: str
    abstract: str | None = None
    full_text: str | None = None
    authors: list[str] = Field(default_factory=list)
    paper_url: str
    pdf_url: str | None = None
    venue: str | None = None
    categories: list[str] = Field(default_factory=list)
    published_at: datetime | None = None
    updated_at_source: datetime | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class SourceFetchResult(BaseModel):
    source: str
    fetched_at: datetime
    papers: list[PaperRecord] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class NotificationSummary(BaseModel):
    destination: str
    summary: str
    generated_at: datetime
    total_records: int = 0
    payload: dict[str, Any] = Field(default_factory=dict)
