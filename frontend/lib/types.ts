export type PaperSource = "arxiv" | "openreview" | "cvf";
export type EditorialPlatform = "bilibili" | "xiaohongshu" | "douyin";
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
  status: "generated" | "reviewed" | "ready-to-export";
  updatedAt: string;
  outputPath: string;
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

export interface PaperRecord {
  paper: PaperItem;
  insight: PaperInsightItem | null;
  notifications: NotificationItem[];
  editorialDrafts: EditorialDraftItem[];
}

export interface DashboardSnapshot {
  metrics: {
    totalPapers: MetricItem;
    papersWithInsights: MetricItem;
    pendingNotifications: MetricItem;
    editorialDrafts: MetricItem;
  };
  recentPapers: PaperRecord[];
  sourceHealth: SourceHealthItem[];
  editorialDrafts: EditorialDraftItem[];
  pipelineStages: PipelineStageItem[];
  notifications: NotificationItem[];
}
