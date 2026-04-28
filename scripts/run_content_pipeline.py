from __future__ import annotations

import argparse
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.config import AppSettings
from app.editorial.pipeline import generate_editorial_files
from app.publish.exporter import default_output_dir
from app.storage import Database
from app.summarization.schemas import PaperInsightRecord


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("--limit must be a positive integer")
    return parsed


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate platform editorial drafts from stored paper insights.")
    parser.add_argument("--limit", type=_positive_int, default=3, help="Maximum number of papers with insights to export")
    parser.add_argument(
        "--base-dir",
        default=str(Path.cwd()),
        help="Base directory where outputs/editorial will be written",
    )
    return parser


def _to_insight_record(insight_model) -> PaperInsightRecord:
    return PaperInsightRecord(
        summary_short=insight_model.summary_short,
        summary_long=insight_model.summary_long,
        novelty_points=list(insight_model.novelty_points or []),
        limitations=list(insight_model.limitations or []),
        applications=list(insight_model.applications or []),
        confidence_score=insight_model.confidence_score,
    )


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    settings = AppSettings()
    db = Database(settings.database_url)
    db.create_schema()

    rows = db.list_papers_with_insights(limit=args.limit)
    if not rows:
        print("no papers with insights found; run python run_once.py first")
        return 1

    output_dir = default_output_dir(Path(args.base_dir).resolve())
    pairs = [(paper, _to_insight_record(insight)) for paper, insight in rows]
    result = generate_editorial_files(papers_with_insights=pairs, output_dir=output_dir, db=db)
    print(f"generated={result.generated}")
    for path in result.outputs:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
