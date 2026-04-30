from __future__ import annotations

from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import httpx

from app.schemas import PaperRecord
from app.sources.base import BaseSource


class OpenReviewSource(BaseSource):
    name = "openreview"

    def __init__(
        self,
        *,
        base_url: str = "https://api2.openreview.net",
        venues: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
        lookback_days: int | None = None,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._site_base_url = self._derive_site_base_url(base_url)
        super().__init__(base_url=self._derive_notes_url(base_url), timeout=timeout, transport=transport)
        self.venues = list(venues or ["CVPR", "ICCV", "ECCV"])
        self._venue_tokens = [venue.lower() for venue in self.venues]
        self.limit = limit
        self.offset = offset
        self.lookback_days = lookback_days

    def fetch(self) -> list[PaperRecord]:
        records: list[PaperRecord] = []
        seen_ids: set[str] = set()

        for venue in self.venues:
            response = self._get(params=self._build_query_params(venue=venue))
            payload = response.json()
            notes = payload.get("notes", [])

            for note in notes:
                record = self._parse_note(note)
                if record is None:
                    continue
                if self._venue_matches(record.venue):
                    if record.source_paper_id in seen_ids:
                        continue
                    seen_ids.add(record.source_paper_id)
                    records.append(record)

        return records

    def _build_query_params(self, *, venue: str | None = None) -> dict[str, str | int]:
        params: dict[str, str | int] = {
            "limit": self.limit,
            "offset": self.offset,
        }
        if venue is not None:
            params["content.venue"] = venue
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

        venue = note.get("venue") or self._get_content_value(content, "venue") or self._get_content_value(content, "venueid")
        pdf_path = (note.get("details") or {}).get("pdf")
        pdf_url = self._build_absolute_url(pdf_path) if pdf_path else self._build_pdf_url(note_id)

        return PaperRecord(
            source="openreview",
            source_paper_id=note_id,
            title=str(title).strip(),
            abstract=str(abstract).strip() if abstract else None,
            full_text=self._fetch_full_text(pdf_url),
            authors=[str(author).strip() for author in authors if str(author).strip()],
            paper_url=self._build_forum_url(forum),
            pdf_url=pdf_url,
            venue=str(venue).strip() if venue else None,
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
        return any(token in venue_lower for token in self._venue_tokens)

    def _build_absolute_url(self, path: str | None) -> str | None:
        if not path:
            return None
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return urljoin(f"{self._site_base_url.rstrip('/')}/", path.lstrip("/"))

    def _build_forum_url(self, forum: str) -> str:
        return self._with_query(path="/forum", query={"id": forum})

    def _build_pdf_url(self, note_id: str) -> str:
        return self._with_query(path="/pdf", query={"id": note_id})

    def _with_query(self, *, path: str, query: dict[str, str]) -> str:
        parsed = urlparse(self._site_base_url)
        return urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                path,
                "",
                urlencode(query),
                "",
            )
        )

    @staticmethod
    def _derive_notes_url(base_url: str) -> str:
        normalized = base_url.rstrip("/")
        parsed = urlparse(normalized)
        if parsed.path.rstrip("/").endswith("/notes") or parsed.path == "/notes":
            return normalized
        return f"{normalized}/notes"

    @staticmethod
    def _derive_site_base_url(base_url: str) -> str:
        parsed = urlparse(base_url)
        if parsed.netloc in {"api.openreview.net", "api2.openreview.net"}:
            return "https://openreview.net"

        path = parsed.path.rstrip("/")
        if path.endswith("/notes"):
            path = path[: -len("/notes")]
        query = urlencode(dict(parse_qsl(parsed.query)))
        return urlunparse((parsed.scheme, parsed.netloc, path, "", query, "")).rstrip("/")

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
