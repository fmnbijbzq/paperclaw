import type {
  EditorialDraftItem,
  NotificationItem,
  PaperInsightItem,
  PaperItem,
  PaperRecord,
  PaperSource,
  PipelineStageItem,
  SourceHealthItem,
} from "./types.ts";

export const API_SCHEMA_VERSION = "2026-04-27";

export type ApiDataSource = "demo" | "http";
export type NotificationDeliveryStatus = "delivered" | "failed" | "pending";

export interface ApiMeta {
  dataSource: ApiDataSource;
  generatedAt: string;
  schemaVersion: string;
}

export interface ApiEnvelope<TData> {
  data: TData;
  meta: ApiMeta;
}

export interface PapersListRequest {
  query?: string;
  source?: PaperSource;
  limit?: number;
}

export interface PaperListItemContract {
  paper: PaperItem;
  insight: Pick<PaperInsightItem, "insightId" | "summaryShort" | "confidenceScore" | "updatedAt"> | null;
  notificationSummary: {
    totalAttempts: number;
    latestStatus: NotificationDeliveryStatus;
    lastSentAt: string | null;
  };
  editorialDraftCount: number;
}

export interface PapersListResponse {
  items: PaperListItemContract[];
  total: number;
  appliedQuery: string;
}

export interface PaperInsightsResponse {
  items: PaperInsightItem[];
  total: number;
}

export interface EditorialDraftsResponse {
  items: EditorialDraftItem[];
  total: number;
}

export interface PaperDetailRequest {
  paperId: number;
}

export interface PaperDetailResponse {
  record: PaperRecord | null;
}

export interface PipelineSummaryRequest {
  source?: PaperSource;
}

export interface PipelineSummaryResponse {
  metrics: {
    totalPapers: number;
    papersWithInsights: number;
    pendingNotifications: number;
    editorialDrafts: number;
  };
  stages: PipelineStageItem[];
  sourceHealth: SourceHealthItem[];
}

export interface NotificationsListRequest {
  paperId?: number;
  onlyFailed?: boolean;
  limit?: number;
}

export interface NotificationFeedItemContract {
  notification: NotificationItem;
  paperTitle: string;
  source: PaperSource;
}

export interface NotificationFeedResponse {
  items: NotificationFeedItemContract[];
  total: number;
  failedCount: number;
  successfulCount: number;
}

interface CreateApiMetaOptions {
  dataSource?: ApiDataSource;
  generatedAt?: string;
}

export function createApiMeta(options: CreateApiMetaOptions = {}): ApiMeta {
  return {
    dataSource: options.dataSource ?? "demo",
    generatedAt: options.generatedAt ?? new Date().toISOString(),
    schemaVersion: API_SCHEMA_VERSION,
  };
}

export function createApiEnvelope<TData>(data: TData, options: CreateApiMetaOptions = {}): ApiEnvelope<TData> {
  return {
    data,
    meta: createApiMeta(options),
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object";
}

function isApiDataSource(value: unknown): value is ApiDataSource {
  return value === "demo" || value === "http";
}

export function isApiEnvelope<TData>(value: unknown): value is ApiEnvelope<TData> {
  if (!isRecord(value) || !("meta" in value) || !("data" in value)) {
    return false;
  }

  const { meta } = value;

  if (!isRecord(meta)) {
    return false;
  }

  return (
    typeof meta.generatedAt === "string" &&
    typeof meta.schemaVersion === "string" &&
    isApiDataSource(meta.dataSource)
  );
}

export function parseApiEnvelope<TData>(value: unknown): ApiEnvelope<TData> {
  if (!isApiEnvelope<TData>(value)) {
    throw new Error("Invalid API envelope.");
  }

  return value;
}
