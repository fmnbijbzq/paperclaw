from __future__ import annotations

from datetime import datetime
from pathlib import Path


def export_reviewed_markdown(*, source_dir: Path, destination_dir: Path) -> list[Path]:
    destination_dir.mkdir(parents=True, exist_ok=True)
    exported: list[Path] = []
    for file in sorted(source_dir.glob("*.md")):
        target = destination_dir / file.name
        target.write_text(file.read_text(encoding="utf-8"), encoding="utf-8")
        exported.append(target)
    return exported


def default_output_dir(base: Path) -> Path:
    return base / "outputs" / "editorial" / datetime.utcnow().strftime("%Y-%m-%d")
