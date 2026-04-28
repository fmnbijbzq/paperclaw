from __future__ import annotations

from datetime import timezone
from pathlib import Path

from app.api.schemas import EditorialDraftDetailResponse, EditorialDraftItem, ExportRecordItem
from app.api.services.read_models import _paper_to_item
from app.models import EditorialDraft, ExportRecord, Paper
from app.publish.exporter import export_reviewed_markdown
from app.storage import Database


def _iso(value) -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


def _draft_to_item(draft: EditorialDraft) -> EditorialDraftItem:
    return EditorialDraftItem(
        draftId=draft.draft_id,
        paperId=draft.paper_id,
        platform=draft.platform,
        title=draft.title,
        hook=draft.hook,
        status=draft.status,
        assignee=draft.assignee,
        updatedAt=_iso(draft.updated_at),
        outputPath=draft.output_path,
    )


def _export_to_item(record: ExportRecord) -> ExportRecordItem:
    return ExportRecordItem(
        exportId=record.export_id,
        draftId=record.draft_id,
        exportedBy=record.exported_by,
        success=record.success,
        sourcePath=record.source_path,
        destinationPath=record.destination_path,
        errorMessage=record.error_message,
        createdAt=_iso(record.created_at),
    )


def list_drafts(db: Database, *, status: str | None = None) -> list[EditorialDraftItem]:
    return [_draft_to_item(item) for item in db.list_editorial_drafts(status=status)]


def get_draft_detail(db: Database, draft_id: str) -> EditorialDraftDetailResponse | None:
    draft = db.get_editorial_draft(draft_id)
    if draft is None:
        return None
    with db._session() as session:
        paper = session.get(Paper, draft.paper_id)
    if paper is None:
        return None
    return EditorialDraftDetailResponse(
        **_draft_to_item(draft).model_dump(by_alias=True),
        markdownContent=draft.markdown_content,
        reviewNote=draft.review_note,
        paper=_paper_to_item(paper),
    )


def export_draft(db: Database, *, draft_id: str, exported_by: str) -> ExportRecordItem:
    draft = db.get_editorial_draft(draft_id)
    if draft is None:
        raise ValueError(f"editorial draft {draft_id} does not exist")
    if draft.status != "approved":
        db.record_export_failure(
            draft_id=draft.draft_id,
            exported_by=exported_by,
            source_path=draft.output_path,
            error_message=f"draft {draft.draft_id} must be approved before export",
        )
        raise ValueError(f"draft {draft.draft_id} must be approved before export")
    source_path = Path(draft.output_path)
    if not source_path.exists():
        source_path.parent.mkdir(parents=True, exist_ok=True)
        source_path.write_text(draft.markdown_content, encoding="utf-8")
    destination_dir = source_path.parent.parent.parent / "exported" / source_path.parent.name
    exported = export_reviewed_markdown(
        source_dir=source_path.parent,
        destination_dir=destination_dir,
        file_glob=source_path.name,
        db=db,
        exported_by=exported_by,
    )
    target = next((path for path in exported if path.name == source_path.name), None)
    if target is None:
        raise ValueError(f"draft {draft.draft_id} did not produce an exported file")
    records = db.list_export_records()
    matching_records = [record for record in records if record.destination_path == str(target)]
    if not matching_records:
        raise ValueError(f"draft {draft.draft_id} did not record an export audit row")
    return _export_to_item(matching_records[-1])


def list_exports(db: Database) -> list[ExportRecordItem]:
    return [_export_to_item(item) for item in db.list_export_records()]
