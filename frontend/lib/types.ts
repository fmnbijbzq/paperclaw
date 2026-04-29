export type PaperSource = "arxiv" | "openreview" | "cvf";
export type EditorialPlatform = "bilibili" | "xiaohongshu" | "douyin";
export type DraftStatus = "generated" | "in_review" | "approved" | "rejected" | "exported";
export type StageStatus = "live" | "partial" | "planned";
export type HealthStatus = "healthy" | "degraded" | "attention";

export interface PaperItem {
  paperId: number;
  sourcePaperId: string;
  title: string;
  abstract: string;
  authors: string[];
  source: PaperSource;
  venue: string;
  categories: string[];
  paperUrl: string;
  pdfUrl: string;
  publishedAt: string;
  updatedAtSource: string;
}

export interface PaperInsightItem {
  insightId: number;
  paperId: number;
  summaryShort: string;
  summaryLong: string;
  noveltyPoints: string[];
  limitations: string[];
  applications: string[];
  confidenceScore: number;
  updatedAt: string;
}

export interface NotificationItem {
  notificationId: number;
  destination: string;
  paperId: number;
  success: boolean;
  errorMessage: string | null;
  sentAt: string;
}

export interface EditorialDraftItem {
  draftId: string;
  paperId: number;
  platform: EditorialPlatform;
  title: string;
  hook: string;
  status: DraftStatus;
  assignee: string | null;
  updatedAt: string;
  outputPath: string;
}

export interface DraftDetailItem extends EditorialDraftItem {
  markdownContent: string;
  reviewNote: string | null;
  paper: PaperItem;
}

export interface ExportRecordItem {
  exportId: number;
  draftId: string;
  exportedBy: string;
  success: boolean;
  sourcePath: string;
  destinationPath: string | null;
  errorMessage: string | null;
  createdAt: string;
}

export interface SourceHealthItem {
  source: PaperSource;
  enabled: boolean;
  status: HealthStatus;
  lastRunAt: string;
  fetchedCount: number;
  newCount: number;
  notes: string;
}

export interface PipelineStageItem {
  stageId: string;
  name: string;
  status: StageStatus;
  summary: string;
  implementedIn: string[];
  evidence: string;
}

export interface MetricItem {
  label: string;
  value: number;
  detail: string;
}

export interface DashboardMetrics {
  totalPapers: MetricItem;
  papersWithInsights: MetricItem;
  pendingNotifications: MetricItem;
  editorialDrafts: MetricItem;
}

export interface PaperRecord {
  paper: PaperItem;
  insight: PaperInsightItem | null;
  notifications: NotificationItem[];
  editorialDrafts: EditorialDraftItem[];
}

export interface NotificationFeedRow {
  notification: NotificationItem;
  paperTitle: string;
  source: PaperSource;
}

export interface DashboardSnapshot {
  metrics: DashboardMetrics;
  recentPapers: PaperRecord[];
  sourceHealth: SourceHealthItem[];
  editorialDrafts: EditorialDraftItem[];
  pipelineStages: PipelineStageItem[];
  notifications: NotificationItem[];
}

export interface DraftActionInput {
  actor: string;
  note?: string | null;
}

export interface DraftAssignInput {
  assignee: string;
  actor?: string | null;
}

export interface DraftExportInput {
  exportedBy: string;
}

export interface DraftListFilters {
  status?: DraftStatus | "all";
  platform?: EditorialPlatform | "all";
  limit?: number;
}

export interface DraftAuditEvent {
  eventId: string;
  label: string;
  detail: string;
  timestamp: string;
  tone: "success" | "warning" | "danger" | "info" | "neutral";
}

export interface DraftDetailRecord {
  draft: DraftDetailItem;
  exportHistory: ExportRecordItem[];
  auditTrail: DraftAuditEvent[];
}

export interface ExportFeedRow {
  record: ExportRecordItem;
  draftTitle: string;
  platform: EditorialPlatform | null;
  draftStatus: DraftStatus | null;
}

export interface PaperSearchParams {
  q?: string;
  source?: PaperSource | "all";
  category?: string;
  venue?: string;
  hasInsight?: boolean;
  hasDraft?: boolean;
  page?: number;
  pageSize?: number;
}

export interface PaperSearchResult {
  records: PaperRecord[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  appliedQuery: string;
}
