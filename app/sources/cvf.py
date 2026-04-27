from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha1
from html.parser import HTMLParser
import re
from urllib.parse import urljoin

import httpx

from app.schemas import PaperRecord
from app.sources.base import BaseSource


@dataclass
class _PaperNode:
    title: str
    paper_url: str
    pdf_url: str | None = None


class _CVFIndexParser(HTMLParser):
    """Parse CVF index pages by tracking ptitle anchors and nearest PDF links."""

    def __init__(self) -> None:
        super().__init__()
        self._ptitle_tag_stack: list[str] = []
        self._capture_anchor = False
        self._anchor_href: str | None = None
        self._anchor_text_parts: list[str] = []
        self._pending_pdf_url: str | None = None
        self._results: list[_PaperNode] = []

    @property
    def papers(self) -> list[_PaperNode]:
        return self._results

    def handle_starttag(self, tag: str, attrs):
        attrs_dict = {key.lower(): value for key, value in attrs}
        lowered_tag = tag.lower()
        class_attr = (attrs_dict.get("class") or "").lower()
        if "ptitle" in class_attr:
            self._ptitle_tag_stack.append(lowered_tag)

        if lowered_tag == "dt":
            self._pending_pdf_url = None

        if lowered_tag != "a":
            return

        href = attrs_dict.get("href")
        if not href:
            return

        lower_href = href.lower()
        if "pdf" in lower_href:
            if self._results and self._results[-1].pdf_url is None:
                self._results[-1].pdf_url = href
            else:
                self._pending_pdf_url = href
            return

        if self._ptitle_tag_stack:
            self._capture_anchor = True
            self._anchor_href = href
            self._anchor_text_parts = []

    def handle_endtag(self, tag: str):
        lowered = tag.lower()
        if lowered == "a" and self._capture_anchor and self._anchor_href:
            title = " ".join("".join(self._anchor_text_parts).split())
            if title:
                self._results.append(
                    _PaperNode(
                        title=title,
                        paper_url=self._anchor_href,
                        pdf_url=self._pending_pdf_url,
                    )
                )
            self._capture_anchor = False
            self._anchor_href = None
            self._anchor_text_parts = []

        if self._ptitle_tag_stack and lowered == self._ptitle_tag_stack[-1]:
            self._ptitle_tag_stack.pop()

    def handle_data(self, data: str):
        if self._capture_anchor and self._ptitle_tag_stack:
            self._anchor_text_parts.append(data)


class CVFSource(BaseSource):
    name = "cvf"

    def __init__(
        self,
        *,
        base_url: str = "https://openaccess.thecvf.com",
        conferences: list[str] | None = None,
        year: int | None = None,
        max_results: int = 100,
        lookback_days: int | None = None,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        super().__init__(base_url=base_url, timeout=timeout, transport=transport)
        self.conferences = [item.upper() for item in (conferences or ["CVPR", "ICCV", "ECCV"])]
        self.year = year or datetime.now(UTC).year
        self.max_results = max_results
        self.lookback_days = lookback_days

    def fetch(self) -> list[PaperRecord]:
        records: list[PaperRecord] = []
        for conference in self.conferences:
            index_url = self._build_index_url(conference)
            try:
                response = self._get_url(index_url)
            except Exception as exc:
                self.logger.warning("Failed to fetch CVF index %s: %s", index_url, exc)
                continue

            parser = _CVFIndexParser()
            parser.feed(response.text)
            for node in parser.papers:
                record = self._node_to_record(conference=conference, node=node)
                if record is None:
                    continue
                records.append(record)
                if len(records) >= self.max_results:
                    return records

        return records

    def _build_index_url(self, conference: str) -> str:
        return f"{self.base_url.rstrip('/')}/{conference}{self.year}"

    def _node_to_record(self, *, conference: str, node: _PaperNode) -> PaperRecord | None:
        title = " ".join(node.title.split())
        if not title:
            return None

        paper_url = urljoin(f"{self.base_url.rstrip('/')}/", node.paper_url)
        pdf_url = urljoin(f"{self.base_url.rstrip('/')}/", node.pdf_url) if node.pdf_url else None
        source_id = self._build_source_paper_id(conference=conference, paper_url=paper_url)

        return PaperRecord(
            source="cvf",
            source_paper_id=source_id,
            title=title,
            abstract=None,
            full_text=self._fetch_full_text(pdf_url),
            authors=[],
            paper_url=paper_url,
            pdf_url=pdf_url,
            venue=f"{conference} {self.year}",
            categories=[conference],
            published_at=None,
            updated_at_source=None,
            raw_payload={
                "conference": conference,
                "year": self.year,
                "paper_url": paper_url,
                "pdf_url": pdf_url,
                "lookback_days": self.lookback_days,
            },
        )

    @staticmethod
    def _build_source_paper_id(*, conference: str, paper_url: str) -> str:
        slug = paper_url.rstrip("/").split("/")[-1]
        slug = re.sub(r"[^a-zA-Z0-9._-]", "-", slug)
        if slug:
            return f"{conference.lower()}:{slug}"
        return f"{conference.lower()}:{sha1(paper_url.encode('utf-8')).hexdigest()[:16]}"
