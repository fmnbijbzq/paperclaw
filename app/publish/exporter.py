from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.storage import Database


def export_reviewed_markdown(
    *,
    source_dir: Path,
    destination_dir: Path,
    file_glob: str = "*.md",
    db: Database | None = None,
    exported_by: str = "system",
) -> list[Path]:
    destination_dir.mkdir(parents=True, exist_ok=True)
    exported: list[Path] = []
    for file in sorted(source_dir.glob(file_glob)):
        if db is not None:
            matching = [draft for draft in db.list_editorial_drafts() if Path(draft.output_path) == file]
            if not matching:
                raise ValueError(f"missing editorial draft record for {file}")
            draft = matching[0]
            if draft.status != "approved":
                db.record_export_failure(
                    draft_id=draft.draft_id,
                    exported_by=exported_by,
                    source_path=str(file),
                    error_message=f"draft {draft.draft_id} must be approved before export",
                )
                raise ValueError(f"draft {draft.draft_id} must be approved before export")
        target = destination_dir / file.name
        target.write_text(file.read_text(encoding="utf-8"), encoding="utf-8")
        if db is not None:
            db.record_export_success(
                draft_id=draft.draft_id,
                exported_by=exported_by,
                source_path=str(file),
                destination_path=str(target),
            )
        exported.append(target)
    return exported


def default_output_dir(base: Path) -> Path:
    return base / "outputs" / "editorial" / datetime.utcnow().strftime("%Y-%m-%d")
