from __future__ import annotations

from pathlib import Path

from app.api.schemas import EditorialDraftItem


def _extract_value(lines: list[str], prefix: str) -> str:
    needle = f"{prefix}:"
    for line in lines:
        if line.startswith(needle):
            return line.split(":", 1)[1].strip()
    return ""


def list_editorial_drafts(root: Path) -> list[EditorialDraftItem]:
    if not root.exists():
        return []

    drafts: list[EditorialDraftItem] = []
    for file in sorted(root.rglob("*.md")):
        content = file.read_text(encoding="utf-8")
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        title = lines[0].removeprefix("# ").strip() if lines else file.stem
        hook = _extract_value(lines, "Hook")
        paper_id_raw = _extract_value(lines, "Paper ID")
        platform = _extract_value(lines, "Platform") or file.stem.split("-", 1)[0]
        status = _extract_value(lines, "Status") or "generated"
        updated_at = file.stat().st_mtime
        drafts.append(
            EditorialDraftItem(
                draftId=file.stem,
                paperId=int(paper_id_raw or 0),
                platform=platform,
                title=title,
                hook=hook,
                status=status,
                updatedAt=file.stat().st_mtime_ns and __import__("datetime").datetime.fromtimestamp(updated_at, tz=__import__("datetime").timezone.utc).isoformat().replace("+00:00", "Z"),
                outputPath=str(file),
            )
        )
    return drafts
