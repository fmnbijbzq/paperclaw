from __future__ import annotations

import re
from typing import Iterable

_PUNCTUATION_RE = re.compile(r"[^\w\s]")
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_title(value: str) -> str:
    cleaned = _PUNCTUATION_RE.sub("", value).lower()
    collapsed = _WHITESPACE_RE.sub(" ", cleaned).strip()
    return collapsed


def _normalize_token(value: str | None) -> str | None:
    if not value:
        return None

    cleaned = _PUNCTUATION_RE.sub("", value).lower()
    collapsed = _WHITESPACE_RE.sub(" ", cleaned).strip()
    return collapsed or None


def build_dedup_key(
    title: str,
    first_author: str | None = None,
    year: int | None = None,
    extras: Iterable[str | None] | None = None,
) -> str:
    parts: list[str] = [normalize_title(title)]
    tokens = [_normalize_token(first_author)]
    if extras:
        tokens.extend(_normalize_token(x) for x in extras)

    tokens = [token for token in tokens if token]
    parts.extend(tokens)

    if year is not None:
        parts.append(str(year))

    return "|".join(parts)
