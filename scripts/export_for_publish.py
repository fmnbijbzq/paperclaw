from __future__ import annotations

import argparse
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.publish.exporter import export_reviewed_markdown


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export reviewed drafts into a publish-ready folder.")
    parser.add_argument("--date", required=True, help="Draft date folder, e.g. 2026-04-27")
    parser.add_argument(
        "--platform",
        choices=["all", "bilibili", "xiaohongshu", "douyin"],
        default="all",
        help="Optional platform subfolder to export (bilibili/xiaohongshu/douyin)",
    )
    parser.add_argument(
        "--base-dir",
        default=str(Path.cwd()),
        help="Base directory containing outputs/editorial and outputs/exported",
    )
    return parser


def _resolve_paths(*, base_dir: Path, date_value: str) -> tuple[Path, Path]:
    source = base_dir / "outputs" / "editorial" / date_value
    destination = base_dir / "outputs" / "exported" / date_value
    return source, destination


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    platform = args.platform.lower()
    source, destination = _resolve_paths(base_dir=Path(args.base_dir).resolve(), date_value=args.date)
    if not source.exists():
        print(f"no source drafts: {source}")
        return 1

    file_glob = "*.md"
    if platform != "all":
        file_glob = f"{platform}-*.md"
        if not any(source.glob(file_glob)):
            print(f"no platform drafts: {source} ({file_glob})")
            return 1

    exported = export_reviewed_markdown(source_dir=source, destination_dir=destination, file_glob=file_glob)
    print(f"exported={len(exported)}")
    for file in exported:
        print(file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
