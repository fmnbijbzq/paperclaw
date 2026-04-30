import { draftsRepository } from "./repositories/drafts.ts";
import { exportsRepository } from "./repositories/exports.ts";
import { notificationsRepository } from "./repositories/notifications.ts";
import { papersRepository, type PaperRepositoryRecord } from "./repositories/papers.ts";
import { pipelineRepository } from "./repositories/pipeline.ts";
import type {
  DashboardSnapshot,
  DraftActionInput,
  DraftAssignInput,
  DraftAuditEvent,
  DraftDetailItem,
  DraftDetailRecord,
  DraftExportInput,
  DraftListFilters,
  EditorialDraftItem,
  EditorialPlatform,
  ExportFeedRow,
  ExportRecordItem,
  NotificationItem,
  PaperRecord,
  PaperSearchParams,
  PaperSearchResult,
  PaperSource,
  PipelineRunsSnapshot,
  PipelineTaskCreateInput,
  PipelineTaskItem,
  DraftStatus,
} from "./types.ts";

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

export async function searchPapers(params: PaperSearchParams | string = {}): Promise<PaperSearchResult> {
  const result = await papersRepository.search(params);

  const notifications = await notificationsRepository.listFeed();
  const notificationsByPaperId = buildNotificationsByPaperId(notifications);

  return {
    ...result,
    records: result.records.map((record) => hydratePaperRecord(record, notificationsByPaperId)),
  };
}

export async function getNotificationFeed(): Promise<NotificationItem[]> {
  return notificationsRepository.listFeed();
}

export async function getSourceHealthBySource(source: PaperSource) {
  return pipelineRepository.getSourceHealthBySource(source);
}

export async function getDraftList(filters?: DraftListFilters): Promise<EditorialDraftItem[]> {
  return draftsRepository.listDrafts(filters);
}

export async function getDraftDetail(draftId: string): Promise<DraftDetailRecord | null> {
  const draft = await draftsRepository.getDraftDetail(draftId);

  if (!draft) {
    return null;
  }

  const allExports = await exportsRepository.listExportRecords();
  const draftExports = allExports.filter((record) => record.draftId === draftId);

  const auditTrail: DraftAuditEvent[] = [];

  auditTrail.push({
    eventId: `${draftId}-created`,
    label: "草稿已生成",
    detail: `已为 ${draft.platform} 平台创建编辑草稿。`,
    timestamp: draft.updatedAt,
    tone: "info",
  });

  if (draft.status === "approved" || draft.status === "exported") {
    auditTrail.push({
      eventId: `${draftId}-approved`,
      label: "草稿已批准",
      detail: `草稿已标记为批准${draft.assignee ? `，负责人：${draft.assignee}` : ""}。`,
      timestamp: draft.updatedAt,
      tone: "success",
    });
  }

  if (draft.status === "rejected") {
    auditTrail.push({
      eventId: `${draftId}-rejected`,
      label: "草稿已驳回",
      detail: draft.reviewNote ?? "草稿已被驳回。",
      timestamp: draft.updatedAt,
      tone: "danger",
    });
  }

  if (draft.status === "in_review") {
    auditTrail.push({
      eventId: `${draftId}-reviewed`,
      label: "审核已开始",
      detail: draft.reviewNote ?? "草稿已进入审核。",
      timestamp: draft.updatedAt,
      tone: "warning",
    });
  }

  for (const exportRecord of draftExports) {
    auditTrail.push({
      eventId: `export-${exportRecord.exportId}`,
      label: exportRecord.success ? "导出成功" : "导出失败",
      detail: exportRecord.success
        ? `${exportRecord.exportedBy} 已导出到 ${exportRecord.destinationPath}。`
        : `${exportRecord.exportedBy} 导出失败：${exportRecord.errorMessage}`,
      timestamp: exportRecord.createdAt,
      tone: exportRecord.success ? "success" : "danger",
    });
  }

  auditTrail.sort((left, right) => new Date(right.timestamp).getTime() - new Date(left.timestamp).getTime());

  return {
    draft,
    exportHistory: draftExports,
    auditTrail,
  };
}

export async function reviewDraft(draftId: string, payload: DraftActionInput): Promise<DraftDetailItem> {
  return draftsRepository.reviewDraft(draftId, payload);
}

export async function approveDraft(draftId: string, payload: DraftActionInput): Promise<DraftDetailItem> {
  return draftsRepository.approveDraft(draftId, payload);
}

export async function rejectDraft(draftId: string, payload: DraftActionInput): Promise<DraftDetailItem> {
  return draftsRepository.rejectDraft(draftId, payload);
}

export async function assignDraft(draftId: string, payload: DraftAssignInput): Promise<DraftDetailItem> {
  return draftsRepository.assignDraft(draftId, payload);
}

export async function exportDraft(draftId: string, payload: DraftExportInput): Promise<ExportRecordItem> {
  return draftsRepository.exportDraft(draftId, payload);
}

export async function getDraftStatusCounts(): Promise<Record<DraftStatus, number>> {
  return draftsRepository.getDraftStatusCounts();
}

export async function getDraftPlatformCounts(): Promise<Record<EditorialPlatform, number>> {
  return draftsRepository.getDraftPlatformCounts();
}

export async function getExportRecords(): Promise<ExportFeedRow[]> {
  const [exports, drafts] = await Promise.all([
    exportsRepository.listExportRecords(),
    draftsRepository.listDrafts(),
  ]);

  const draftMap = new Map(drafts.map((draft) => [draft.draftId, draft]));

  return exports.map((record) => {
    const draft = draftMap.get(record.draftId);

    return {
      record,
      draftTitle: draft?.title ?? `Draft ${record.draftId}`,
      platform: draft?.platform ?? null,
      draftStatus: draft?.status ?? null,
    };
  });
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

export async function getPipelineRunsSnapshot(): Promise<PipelineRunsSnapshot> {
  const [crawlRuns, summarizationRuns, editorialRuns] = await Promise.all([
    pipelineRepository.listCrawlRuns(),
    pipelineRepository.listSummarizationRuns(),
    pipelineRepository.listEditorialRuns(),
  ]);

  return {
    crawlRuns,
    summarizationRuns,
    editorialRuns,
  };
}

export async function getPipelineTasks(): Promise<PipelineTaskItem[]> {
  return pipelineRepository.listPipelineTasks();
}

export async function createPipelineTask(input: PipelineTaskCreateInput): Promise<PipelineTaskItem> {
  return pipelineRepository.createPipelineTask(input);
}

export async function getPipelineTask(taskId: number): Promise<PipelineTaskItem | null> {
  return pipelineRepository.getPipelineTask(taskId);
}

export async function cancelPipelineTask(taskId: number): Promise<PipelineTaskItem> {
  return pipelineRepository.cancelPipelineTask(taskId);
}
