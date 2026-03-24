from __future__ import annotations

from app.schemas import PaperRecord
from app.utils.hashers import build_dedup_key


def normalize_paper(record: PaperRecord) -> PaperRecord:
    if record.dedup_key:
        return record

    year = record.published_at.year if record.published_at else None
    first_author = record.authors[0] if record.authors else None

    return record.model_copy(
        update={
            "dedup_key": build_dedup_key(
                title=record.title,
                first_author=first_author,
                year=year,
            )
        }
    )
