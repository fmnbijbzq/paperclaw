from pathlib import Path
import sys

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from app.schemas import PaperRecord
from app.storage import Database
from scripts import review_queue


def _seed_draft(tmp_path: Path) -> tuple[Database, str, str]:
    database_url = f"sqlite:///{tmp_path/'papers.db'}"
    db = Database(database_url)
    db.create_schema()
    paper = db.upsert_paper(
        PaperRecord(
            source="demo",
            source_paper_id="demo-1",
            title="Demo Paper",
            abstract="Abstract.",
            paper_url="https://example.test/paper",
        )
    )
    draft = db.upsert_editorial_draft(
        paper_id=paper.paper_id,
        platform="bilibili",
        title="Draft Title",
        hook="Draft hook",
        markdown_content="# Draft Title\n",
        output_path=str(tmp_path / "outputs" / "editorial" / "draft.md"),
    )
    return db, database_url, draft.draft_id


def test_review_queue_list_prints_pending_drafts(tmp_path, capsys):
    _, database_url, draft_id = _seed_draft(tmp_path)

    exit_code = review_queue.main(["--database-url", database_url, "list"])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert draft_id in output
    assert "generated" in output
    assert "Draft Title" in output


def test_review_queue_approve_generated_draft(tmp_path):
    db, database_url, draft_id = _seed_draft(tmp_path)

    exit_code = review_queue.main(["--database-url", database_url, "approve", draft_id])

    stored = db.get_editorial_draft(draft_id)
    assert exit_code == 0
    assert stored is not None
    assert stored.status == "approved"
    assert stored.approved_by == "review_queue"


def test_review_queue_reject_generated_draft(tmp_path):
    db, database_url, draft_id = _seed_draft(tmp_path)

    exit_code = review_queue.main(["--database-url", database_url, "reject", draft_id, "--note", "needs rewrite"])

    stored = db.get_editorial_draft(draft_id)
    assert exit_code == 0
    assert stored is not None
    assert stored.status == "rejected"
    assert stored.review_note == "needs rewrite"
