from __future__ import annotations

import argparse
from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.config import AppSettings
from app.models import EditorialDraft
from app.storage import Database

PENDING_STATUSES = {"generated", "in_review"}
DEFAULT_ACTOR = "review_queue"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Review generated editorial drafts.")
    parser.add_argument("--database-url", help="Override DATABASE_URL for the review queue")
    parser.add_argument("--actor", default=DEFAULT_ACTOR, help="Reviewer name recorded on status changes")

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list", help="List drafts waiting for review")

    approve = subparsers.add_parser("approve", help="Approve a draft")
    approve.add_argument("draft_id")
    approve.add_argument("--note", help="Optional review note")

    reject = subparsers.add_parser("reject", help="Reject a draft")
    reject.add_argument("draft_id")
    reject.add_argument("--note", help="Optional rejection note")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    db = _build_database(args.database_url)

    if args.command == "list":
        return _list_pending(db)
    if args.command == "approve":
        return _approve(db, draft_id=args.draft_id, actor=args.actor, note=args.note)
    if args.command == "reject":
        return _reject(db, draft_id=args.draft_id, actor=args.actor, note=args.note)

    raise AssertionError(f"unknown command: {args.command}")


def _build_database(database_url: str | None) -> Database:
    url = database_url or AppSettings().database_url
    db = Database(url)
    db.create_schema()
    return db


def _list_pending(db: Database) -> int:
    drafts = [draft for draft in db.list_editorial_drafts() if draft.status in PENDING_STATUSES]
    if not drafts:
        print("no pending drafts")
        return 0

    print("draft_id\tstatus\tplatform\ttitle")
    for draft in drafts:
        print(f"{draft.draft_id}\t{draft.status}\t{draft.platform}\t{draft.title}")
    return 0


def _approve(db: Database, *, draft_id: str, actor: str, note: str | None) -> int:
    try:
        draft = _ensure_in_review(db, draft_id=draft_id, actor=actor, note=note)
        approved = db.approve_editorial_draft(draft.draft_id, actor=actor, note=note)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"approved {approved.draft_id}")
    return 0


def _reject(db: Database, *, draft_id: str, actor: str, note: str | None) -> int:
    try:
        draft = _ensure_in_review(db, draft_id=draft_id, actor=actor, note=note)
        rejected = db.reject_editorial_draft(draft.draft_id, actor=actor, note=note)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"rejected {rejected.draft_id}")
    return 0


def _ensure_in_review(db: Database, *, draft_id: str, actor: str, note: str | None) -> EditorialDraft:
    draft = db.get_editorial_draft(draft_id)
    if draft is None:
        raise ValueError(f"editorial draft {draft_id} does not exist")
    if draft.status == "in_review":
        return draft
    if draft.status in {"generated", "rejected"}:
        return db.review_editorial_draft(draft_id, actor=actor, note=note)
    raise ValueError(f"draft {draft_id} is not reviewable from status {draft.status}")


if __name__ == "__main__":
    raise SystemExit(main())
