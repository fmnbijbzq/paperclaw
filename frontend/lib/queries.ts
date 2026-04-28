import { notificationsRepository } from "./repositories/notifications.ts";
import { papersRepository, type PaperRepositoryRecord } from "./repositories/papers.ts";
import { pipelineRepository } from "./repositories/pipeline.ts";
import type { DashboardSnapshot, NotificationItem, PaperRecord, PaperSource } from "./types.ts";

function buildNotificationsByPaperId(notifications: NotificationItem[]): Map<number, NotificationItem[]> {
  const notificationsByPaperId = new Map<number, NotificationItem[]>();

  for (const notification of notifications) {
    const existingNotifications = notificationsByPaperId.get(notification.paperId) ?? [];
    existingNotifications.push(notification);
    notificationsByPaperId.set(notification.paperId, existingNotifications);
  }

  return notificationsByPaperId;
}

function hydratePaperRecord(
  record: PaperRepositoryRecord,
  notificationsByPaperId: Map<number, NotificationItem[]>,
): PaperRecord {
  return {
    paper: record.paper,
    insight: record.insight,
    notifications: notificationsByPaperId.get(record.paper.paperId) ?? [],
    editorialDrafts: record.editorialDrafts,
  };
}

function hydratePaperRecords(records: PaperRepositoryRecord[], notifications: NotificationItem[]): PaperRecord[] {
  const notificationsByPaperId = buildNotificationsByPaperId(notifications);

  return records.map((record) => hydratePaperRecord(record, notificationsByPaperId));
}

export async function getPaperDetail(paperId: number): Promise<PaperRecord | null> {
  const [record, notifications] = await Promise.all([
    papersRepository.getRecord(paperId),
    notificationsRepository.listByPaperId(paperId),
  ]);

  if (!record) {
    return null;
  }

  return {
    paper: record.paper,
    insight: record.insight,
    notifications,
    editorialDrafts: record.editorialDrafts,
  };
}

export async function listPaperRecords(): Promise<PaperRecord[]> {
  const [records, notifications] = await Promise.all([
    papersRepository.listRecords(),
    notificationsRepository.listFeed(),
  ]);

  return hydratePaperRecords(records, notifications);
}

export async function searchPapers(query = ""): Promise<PaperRecord[]> {
  const [records, notifications] = await Promise.all([
    papersRepository.search(query),
    notificationsRepository.listFeed(),
  ]);

  return hydratePaperRecords(records, notifications);
}

export async function getNotificationFeed(): Promise<NotificationItem[]> {
  return notificationsRepository.listFeed();
}

export async function getSourceHealthBySource(source: PaperSource) {
  return pipelineRepository.getSourceHealthBySource(source);
}

export async function getDashboardSnapshot(): Promise<DashboardSnapshot> {
  const [paperRecords, notifications, sourceHealth, pipelineStages, editorialDrafts] = await Promise.all([
    papersRepository.listRecords(),
    notificationsRepository.listFeed(),
    pipelineRepository.listSourceHealth(),
    pipelineRepository.listStages(),
    papersRepository.listEditorialDrafts(),
  ]);
  const records = hydratePaperRecords(paperRecords, notifications);
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
        value: records.length,
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
    editorialDrafts,
    pipelineStages,
    notifications,
  };
}
