from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx

from app.schemas import PaperRecord
from app.sources.base import BaseSource


class OpenReviewSource(BaseSource):
    name = "openreview"

    def __init__(
        self,
        *,
        base_url: str = "https://api.openreview.net",
        venues: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
        lookback_days: int | None = None,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        super().__init__(base_url=base_url, timeout=timeout, transport=transport)
        self.venues = [venue.lower() for venue in (venues or [])]
        self.limit = limit
        self.offset = offset
        self.lookback_days = lookback_days

    def fetch(self) -> list[PaperRecord]:
        response = self._get(params=self._build_query_params())
        payload = response.json()
        notes = payload.get("notes", [])

        records: list[PaperRecord] = []
        for note in notes:
            record = self._parse_note(note)
            if record is None:
                continue
            if self.venues and not self._venue_matches(record.venue):
                continue
            records.append(record)

        return records

    def _build_query_params(self) -> dict[str, str | int]:
        params: dict[str, str | int] = {
            "limit": self.limit,
            "offset": self.offset,
        }
        if self.lookback_days is not None:
            mintcdate = int((datetime.now(UTC) - timedelta(days=self.lookback_days)).timestamp() * 1000)
            params["mintcdate"] = mintcdate
        return params

    def _parse_note(self, note: dict) -> PaperRecord | None:
        note_id = note.get("id")
        content = note.get("content", {})
        title = self._get_content_value(content, "title")
        forum = note.get("forum")

        if not note_id or not title or not forum:
            return None

        abstract = self._get_content_value(content, "abstract")
        authors = self._get_content_value(content, "authors") or []
        if not isinstance(authors, list):
            authors = [str(authors)]

        venue = note.get("venue")
        pdf_path = (note.get("details") or {}).get("pdf")
        pdf_url = self._build_absolute_url(pdf_path)

        return PaperRecord(
            source="openreview",
            source_paper_id=note_id,
            title=str(title).strip(),
            abstract=str(abstract).strip() if abstract else None,
            full_text=self._fetch_full_text(pdf_url),
            authors=[str(author).strip() for author in authors if str(author).strip()],
            paper_url=f"{self.base_url.rstrip('/')}/forum?id={forum}",
            pdf_url=pdf_url,
            venue=venue,
            published_at=self._from_millis(note.get("cdate")),
            updated_at_source=self._from_millis(note.get("mdate")),
            raw_payload={
                "id": note_id,
                "forum": forum,
                "venue": venue,
            },
        )

    def _venue_matches(self, venue: str | None) -> bool:
        if not venue:
            return False
        venue_lower = venue.lower()
        return any(token in venue_lower for token in self.venues)

    def _build_absolute_url(self, path: str | None) -> str | None:
        if not path:
            return None
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"

    @staticmethod
    def _get_content_value(content: dict, key: str):
        value = content.get(key)
        if isinstance(value, dict):
            return value.get("value")
        return value

    @staticmethod
    def _from_millis(value: int | None) -> datetime | None:
        if value is None:
            return None
        return datetime.fromtimestamp(value / 1000, tz=UTC)
