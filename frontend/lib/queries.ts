import { editorialDrafts, insights, notifications, papers, pipelineStages, sourceHealth } from "./demo-data.ts";
import type {
  DashboardSnapshot,
  EditorialDraftItem,
  NotificationItem,
  PaperRecord,
  PaperSource,
} from "./types.ts";

function compareDesc(left: string, right: string): number {
  return new Date(right).getTime() - new Date(left).getTime();
}

function getInsightByPaperId(paperId: number) {
  return insights.find((insight) => insight.paperId === paperId) ?? null;
}

function getNotificationsByPaperId(paperId: number): NotificationItem[] {
  return notifications
    .filter((notification) => notification.paperId === paperId)
    .sort((left, right) => compareDesc(left.sentAt, right.sentAt));
}

function getDraftsByPaperId(paperId: number): EditorialDraftItem[] {
  return editorialDrafts
    .filter((draft) => draft.paperId === paperId)
    .sort((left, right) => compareDesc(left.updatedAt, right.updatedAt));
}

export function getPaperDetail(paperId: number): PaperRecord | null {
  const paper = papers.find((item) => item.paperId === paperId);

  if (!paper) {
    return null;
  }

  return {
    paper,
    insight: getInsightByPaperId(paperId),
    notifications: getNotificationsByPaperId(paperId),
    editorialDrafts: getDraftsByPaperId(paperId),
  };
}

export function listPaperRecords(): PaperRecord[] {
  return [...papers]
    .sort((left, right) => compareDesc(left.publishedAt, right.publishedAt))
    .map((paper) => ({
      paper,
      insight: getInsightByPaperId(paper.paperId),
      notifications: getNotificationsByPaperId(paper.paperId),
      editorialDrafts: getDraftsByPaperId(paper.paperId),
    }));
}

export function searchPapers(query = ""): PaperRecord[] {
  const normalizedQuery = query.trim().toLowerCase();

  if (!normalizedQuery) {
    return listPaperRecords();
  }

  return listPaperRecords().filter(({ paper, insight }) => {
    const haystack = [
      paper.title,
      paper.abstract,
      paper.source,
      paper.venue,
      paper.authors.join(" "),
      paper.categories.join(" "),
      insight?.summaryShort ?? "",
    ]
      .join(" ")
      .toLowerCase();

    return haystack.includes(normalizedQuery);
  });
}

export function getNotificationFeed(): NotificationItem[] {
  return [...notifications].sort((left, right) => compareDesc(left.sentAt, right.sentAt));
}

export function getSourceHealthBySource(source: PaperSource) {
  return sourceHealth.find((item) => item.source === source) ?? null;
}

export function getDashboardSnapshot(): DashboardSnapshot {
  const records = listPaperRecords();
  const papersWithInsights = records.filter((record) => record.insight);
  const successfulNotificationPaperIds = new Set(
    notifications.filter((notification) => notification.success).map((notification) => notification.paperId),
  );
  const pendingNotifications = papersWithInsights.filter(
    (record) => !successfulNotificationPaperIds.has(record.paper.paperId),
  );

  return {
    metrics: {
      totalPapers: {
        label: "Papers stored",
        value: papers.length,
        detail: "Current companion dataset mirrors the backend paper model.",
      },
      papersWithInsights: {
        label: "Insight coverage",
        value: papersWithInsights.length,
        detail: "Papers with generated summaries, novelty, limitations, and applications.",
      },
      pendingNotifications: {
        label: "Pending notifications",
        value: pendingNotifications.length,
        detail: "Insight-ready papers without a successful Feishu delivery yet.",
      },
      editorialDrafts: {
        label: "Editorial drafts",
        value: editorialDrafts.length,
        detail: "Generated markdown artifacts across Bilibili, Xiaohongshu, and Douyin.",
      },
    },
    recentPapers: records.slice(0, 4),
    sourceHealth,
    editorialDrafts: [...editorialDrafts].sort((left, right) => compareDesc(left.updatedAt, right.updatedAt)),
    pipelineStages,
    notifications: getNotificationFeed(),
  };
}
