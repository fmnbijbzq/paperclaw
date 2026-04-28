from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from app.editorial.composer import EditorialComposer, EditorialDraft
from app.storage import Database


@dataclass
class EditorialPipelineResult:
    generated: int
    outputs: list[Path]


def generate_editorial_files(
    *,
    papers_with_insights: list[tuple[object, object]],
    output_dir: Path,
    db: Database | None = None,
) -> EditorialPipelineResult:
    templates_dir = Path(__file__).resolve().parent / "templates"
    composer = EditorialComposer(str(templates_dir))

    output_dir.mkdir(parents=True, exist_ok=True)
    generated_files: list[Path] = []

    for paper, insight in papers_with_insights:
        for platform in ("bilibili", "xiaohongshu", "douyin"):
            draft = composer.compose(platform=platform, paper=paper, insight=insight)
            file_path = _write_draft(output_dir=output_dir, draft=draft, paper=paper)
            generated_files.append(file_path)
            if db is not None:
                db.upsert_editorial_draft(
                    paper_id=getattr(paper, "paper_id"),
                    platform=platform,
                    title=draft.title,
                    hook=draft.hook,
                    markdown_content=file_path.read_text(encoding="utf-8"),
                    output_path=str(file_path),
                )

    return EditorialPipelineResult(generated=len(generated_files), outputs=generated_files)


def _write_draft(*, output_dir: Path, draft: EditorialDraft, paper: object) -> Path:
    slug = _paper_slug(paper)
    file_path = output_dir / f"{draft.platform}-{slug}.md"
    lines = [
        f"# {draft.title}",
        "",
        f"> Hook: {draft.hook}",
        "",
        draft.body,
        "",
        f"Tags: {' '.join('#' + tag for tag in draft.tags)}",
        f"GeneratedAt: {datetime.utcnow().isoformat()}Z",
    ]
    file_path.write_text("\n".join(lines), encoding="utf-8")
    return file_path


def _paper_slug(paper: object) -> str:
    title = getattr(paper, "title", "paper")
    normalized = "".join(ch.lower() if ch.isalnum() else "-" for ch in title)
    while "--" in normalized:
        normalized = normalized.replace("--", "-")
    normalized = normalized.strip("-")
    return normalized[:80] or "paper"
