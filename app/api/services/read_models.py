from __future__ import annotations

from collections import defaultdict
from datetime import timezone
from pathlib import Path

from sqlalchemy import Select, func, select

from app.api.schemas import (
    EditorialDraftSummaryItem,
    NotificationItem,
    NotificationSummaryItem,
    PaperDetailItem,
    PaperInsightItem,
    PaperInsightPreview,
    PaperItem,
    PaperListItem,
)
from app.models import EditorialDraft, Notification, Paper, PaperInsight
from app.storage import Database


def _iso(value) -> str:
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


def _paper_to_item(paper: Paper) -> PaperItem:
    return PaperItem(
        paperId=paper.paper_id,
        sourcePaperId=paper.source_paper_id,
        title=paper.title,
        abstract=paper.abstract or "",
        authors=list(paper.authors or []),
        source=paper.source,
        venue=paper.venue or "",
        categories=list(paper.categories or []),
        paperUrl=paper.paper_url,
        pdfUrl=paper.pdf_url or "",
        publishedAt=_iso(paper.published_at),
        updatedAtSource=_iso(paper.updated_at_source),
    )


def _insight_to_item(insight: PaperInsight) -> PaperInsightItem:
    return PaperInsightItem(
        insightId=insight.insight_id,
        paperId=insight.paper_id,
        summaryShort=insight.summary_short,
        summaryLong=insight.summary_long,
        noveltyPoints=list(insight.novelty_points or []),
        limitations=list(insight.limitations or []),
        applications=list(insight.applications or []),
        confidenceScore=insight.confidence_score,
        isPlaceholder=bool(insight.is_placeholder),
        generator=insight.generator or "template-v1",
        updatedAt=_iso(insight.updated_at),
    )


def _notification_to_item(notification: Notification) -> NotificationItem:
    return NotificationItem(
        notificationId=notification.notification_id,
        destination=notification.destination,
        paperId=notification.paper_id,
        success=notification.success,
        errorMessage=notification.error_message,
        sentAt=_iso(notification.sent_at),
    )


def _draft_to_summary_item(draft: EditorialDraft) -> EditorialDraftSummaryItem:
    return EditorialDraftSummaryItem(
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


def list_paper_insights(db: Database) -> list[PaperInsightItem]:
    with db._session() as session:
        insights = list(session.scalars(select(PaperInsight).order_by(PaperInsight.paper_id.asc())))
    return [_insight_to_item(item) for item in insights]


def _like_pattern(value: str) -> str:
    """构造 LIKE 模式时转义用户输入的 % / _ / \\，避免它们被解释成通配符。

    例如用户搜 "50%"，旧实现会把它当作"任意字符 50 + 任意字符"匹配到所有论文；
    转义后只匹配标题真含 50% 的论文。
    """
    escaped = value.strip().lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _apply_filters(
    stmt: Select[tuple[Paper]],
    *,
    q: str = "",
    source: str | None = None,
    category: str | None = None,
    venue: str | None = None,
    has_insight: bool | None = None,
    has_draft: bool | None = None,
) -> Select[tuple[Paper]]:
    if q:
        like = _like_pattern(q)
        stmt = stmt.where(
            func.lower(Paper.title).like(like, escape="\\")
            | func.lower(func.coalesce(Paper.abstract, "")).like(like, escape="\\")
            | func.lower(Paper.source_paper_id).like(like, escape="\\")
        )
    if source:
        stmt = stmt.where(Paper.source == source)
    if category:
        stmt = stmt.where(
            func.lower(func.coalesce(Paper.categories, "[]")).like(_like_pattern(category), escape="\\")
        )
    if venue:
        stmt = stmt.where(
            func.lower(func.coalesce(Paper.venue, "")).like(_like_pattern(venue), escape="\\")
        )
    if has_insight is not None:
        insight_exists = select(PaperInsight.paper_id).where(PaperInsight.paper_id == Paper.paper_id).exists()
        stmt = stmt.where(insight_exists if has_insight else ~insight_exists)
    if has_draft is not None:
        draft_exists = select(EditorialDraft.paper_id).where(EditorialDraft.paper_id == Paper.paper_id).exists()
        stmt = stmt.where(draft_exists if has_draft else ~draft_exists)
    return stmt


def list_papers(
    db: Database,
    editorial_root: Path,
    *,
    q: str = "",
    source: str | None = None,
    category: str | None = None,
    venue: str | None = None,
    has_insight: bool | None = None,
    has_draft: bool | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> tuple[list[PaperListItem], int]:
    del editorial_root

    with db._session() as session:
        base_stmt = _apply_filters(
            select(Paper),
            q=q,
            source=source,
            category=category,
            venue=venue,
            has_insight=has_insight,
            has_draft=has_draft,
        )
        total = session.scalar(select(func.count()).select_from(base_stmt.subquery())) or 0
        papers_stmt = base_stmt.order_by(Paper.paper_id.asc()).offset(offset)
        if limit is not None:
            papers_stmt = papers_stmt.limit(limit)
        papers = list(session.scalars(papers_stmt))

        # 旧实现对 insights / notifications / editorial_drafts 三张表都做了
        # 全表 SELECT，论文增多后会内存爆。这里只查询当前页 paper_id 范围。
        page_ids = [paper.paper_id for paper in papers]
        if page_ids:
            insights = {
                item.paper_id: item
                for item in session.scalars(
                    select(PaperInsight).where(PaperInsight.paper_id.in_(page_ids))
                )
            }
            notifications_by_paper: dict[int, list[Notification]] = defaultdict(list)
            for notification in session.scalars(
                select(Notification)
                .where(Notification.paper_id.in_(page_ids))
                .order_by(Notification.sent_at.asc())
            ):
                notifications_by_paper[notification.paper_id].append(notification)
            drafts_by_paper: dict[int, int] = {
                paper_id: count
                for paper_id, count in session.execute(
                    select(EditorialDraft.paper_id, func.count(EditorialDraft.draft_id))
                    .where(EditorialDraft.paper_id.in_(page_ids))
                    .group_by(EditorialDraft.paper_id)
                ).all()
            }
        else:
            insights = {}
            notifications_by_paper = defaultdict(list)
            drafts_by_paper = {}

    items: list[PaperListItem] = []
    for paper in papers:
        insight = insights.get(paper.paper_id)
        attempts = notifications_by_paper.get(paper.paper_id, [])
        latest = attempts[-1] if attempts else None
        preview = None
        if insight is not None:
            preview = PaperInsightPreview(
                insightId=insight.insight_id,
                summaryShort=insight.summary_short,
                confidenceScore=insight.confidence_score,
                isPlaceholder=bool(insight.is_placeholder),
                updatedAt=_iso(insight.updated_at),
            )
        items.append(
            PaperListItem(
                paper=_paper_to_item(paper),
                insight=preview,
                notificationSummary=NotificationSummaryItem(
                    totalAttempts=len(attempts),
                    latestStatus=("delivered" if latest and latest.success else "pending" if latest is None else "failed"),
                    lastSentAt=_iso(latest.sent_at) if latest else None,
                ),
                editorialDraftCount=drafts_by_paper.get(paper.paper_id, 0),
            )
        )
    return items, total


def get_paper_detail(db: Database, paper_id: int) -> PaperDetailItem | None:
    with db._session() as session:
        paper = session.get(Paper, paper_id)
        if paper is None:
            return None
        insight = session.scalar(select(PaperInsight).where(PaperInsight.paper_id == paper_id))
        notifications = list(
            session.scalars(
                select(Notification)
                .where(Notification.paper_id == paper_id)
                .order_by(Notification.notification_id.asc())
            )
        )
        drafts = list(
            session.scalars(
                select(EditorialDraft)
                .where(EditorialDraft.paper_id == paper_id)
                .order_by(EditorialDraft.created_at.asc())
            )
        )

    return PaperDetailItem(
        paper=_paper_to_item(paper),
        insight=_insight_to_item(insight) if insight is not None else None,
        notifications=[_notification_to_item(item) for item in notifications],
        drafts=[_draft_to_summary_item(item) for item in drafts],
    )
