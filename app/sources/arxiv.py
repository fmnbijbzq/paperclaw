from __future__ import annotations

from datetime import UTC, datetime, timedelta
import logging
from xml.etree import ElementTree

import httpx

from app.schemas import PaperRecord
from app.sources.base import BaseSource

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


class ArxivSource(BaseSource):
    name = "arxiv"

    def __init__(
        self,
        *,
        base_url: str = "https://export.arxiv.org/api/query",
        search_query: str = "cat:cs.CV",
        start: int = 0,
        max_results: int = 100,
        allowed_categories: list[str] | None = None,
        lookback_days: int | None = None,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        super().__init__(base_url=base_url, timeout=timeout, transport=transport)
        self.search_query = search_query
        self.start = start
        self.max_results = max_results
        self.allowed_categories = set(allowed_categories or [])
        self.lookback_days = lookback_days
        self.logger = logging.getLogger(__name__)

    def fetch(self) -> list[PaperRecord]:
        response = self._get(params=self._build_query_params())
        feed = ElementTree.fromstring(response.text)
        records: list[PaperRecord] = []

        for entry in feed.findall("atom:entry", ATOM_NS):
            record = self._parse_entry(entry)
            if record is None:
                continue
            if self.allowed_categories and not self.allowed_categories.intersection(record.categories):
                continue
            records.append(record)

        return records

    def _build_query_params(self) -> dict[str, str | int]:
        query = self.search_query
        if self.lookback_days is not None:
            since = (datetime.now(UTC) - timedelta(days=self.lookback_days)).strftime("%Y%m%d%H%M")
            query = f"{query} AND lastUpdatedDate:[{since} TO *]"

        return {
            "search_query": query,
            "start": self.start,
            "max_results": self.max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

    def _parse_entry(self, entry: ElementTree.Element) -> PaperRecord | None:
        entry_id = self._clean_text(entry.findtext("atom:id", default="", namespaces=ATOM_NS))
        title = self._clean_text(entry.findtext("atom:title", default="", namespaces=ATOM_NS))

        if not entry_id or not title:
            self.logger.warning("Skipping arXiv entry with missing id/title")
            return None

        categories = [
            category.attrib["term"]
            for category in entry.findall("atom:category", ATOM_NS)
            if category.attrib.get("term")
        ]
        authors = [
            self._clean_text(author.findtext("atom:name", default="", namespaces=ATOM_NS))
            for author in entry.findall("atom:author", ATOM_NS)
        ]
        authors = [author for author in authors if author]

        pdf_url = None
        for link in entry.findall("atom:link", ATOM_NS):
            if link.attrib.get("title") == "pdf" and link.attrib.get("href"):
                pdf_url = link.attrib["href"]
                break

        return PaperRecord(
            source="arxiv",
            source_paper_id=entry_id.rsplit("/", 1)[-1],
            title=title,
            abstract=self._clean_text(entry.findtext("atom:summary", default="", namespaces=ATOM_NS)) or None,
            full_text=self._fetch_full_text(pdf_url),
            authors=authors,
            paper_url=entry_id,
            pdf_url=pdf_url,
            categories=categories,
            published_at=self._parse_datetime(entry.findtext("atom:published", default=None, namespaces=ATOM_NS)),
            updated_at_source=self._parse_datetime(
                entry.findtext("atom:updated", default=None, namespaces=ATOM_NS)
            ),
            raw_payload={
                "id": entry_id,
                "title": title,
                "categories": categories,
            },
        )

    @staticmethod
    def _clean_text(value: str | None) -> str:
        if not value:
            return ""
        return " ".join(value.split())

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        if not value:
            return None
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
