from __future__ import annotations

from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.publish.exporter import export_reviewed_markdown


def _parse_args(argv: list[str]) -> tuple[Path, Path]:
    if "--date" in argv:
        date_value = argv[argv.index("--date") + 1]
    else:
        raise SystemExit("--date is required")

    source = Path(_ROOT) / "outputs" / "editorial" / date_value
    destination = Path(_ROOT) / "outputs" / "exported" / date_value
    return source, destination


def main() -> int:
    source, destination = _parse_args(sys.argv[1:])
    if not source.exists():
        print(f"no source drafts: {source}")
        return 1

    exported = export_reviewed_markdown(source_dir=source, destination_dir=destination)
    print(f"exported={len(exported)}")
    for file in exported:
        print(file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
