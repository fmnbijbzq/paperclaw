import { pipelineStages, sourceHealth } from "../../demo-data.ts";
import type { CrawlRunItem, EditorialRunItem, PipelineStageItem, SourceHealthItem, SummarizationRunItem } from "../../types.ts";

export interface PipelineDataSource {
  listPipelineStages(): Promise<PipelineStageItem[]>;
  listSourceHealth(): Promise<SourceHealthItem[]>;
  listCrawlRuns(): Promise<CrawlRunItem[]>;
  listSummarizationRuns(): Promise<SummarizationRunItem[]>;
  listEditorialRuns(): Promise<EditorialRunItem[]>;
}

export const demoPipelineDataSource: PipelineDataSource = {
  async listPipelineStages() {
    return [...pipelineStages];
  },
  async listSourceHealth() {
    return [...sourceHealth];
  },
  async listCrawlRuns() {
    return [...demoCrawlRuns];
  },
  async listSummarizationRuns() {
    return [...demoSummarizationRuns];
  },
  async listEditorialRuns() {
    return [...demoEditorialRuns];
  },
};

const demoCrawlRuns: CrawlRunItem[] = [
  {
    runId: 10,
    source: "arxiv",
    status: "success",
    fetchedCount: 42,
    newCount: 11,
    errorMessage: null,
    startedAt: "2026-04-26T05:55:00Z",
    finishedAt: "2026-04-26T06:00:00Z",
    durationSeconds: 312.5,
  },
  {
    runId: 9,
    source: "openreview",
    status: "success",
    fetchedCount: 18,
    newCount: 4,
    errorMessage: null,
    startedAt: "2026-04-25T07:52:00Z",
    finishedAt: "2026-04-25T08:00:00Z",
    durationSeconds: 467.2,
  },
  {
    runId: 8,
    source: "cvf",
    status: "failed",
    fetchedCount: 27,
    newCount: 7,
    errorMessage: "CVF page returned HTTP 503 for CVPR 2026 proceedings listing.",
    startedAt: "2026-04-26T08:40:00Z",
    finishedAt: "2026-04-26T09:00:00Z",
    durationSeconds: 1180.0,
  },
  {
    runId: 7,
    source: "arxiv",
    status: "success",
    fetchedCount: 38,
    newCount: 8,
    errorMessage: null,
    startedAt: "2026-04-25T05:50:00Z",
    finishedAt: "2026-04-25T05:58:00Z",
    durationSeconds: 498.1,
  },
  {
    runId: 6,
    source: "openreview",
    status: "failed",
    fetchedCount: 0,
    newCount: 0,
    errorMessage: "Rate limited by OpenReview API after 3 retries.",
    startedAt: "2026-04-24T07:00:00Z",
    finishedAt: "2026-04-24T07:05:00Z",
    durationSeconds: 305.0,
  },
];

const demoSummarizationRuns: SummarizationRunItem[] = [
  {
    runId: 10,
    status: "success",
    papersProcessed: 42,
    insightsGenerated: 42,
    errorMessage: null,
    startedAt: "2026-04-26T06:00:00Z",
    finishedAt: "2026-04-26T06:05:00Z",
    durationSeconds: 310.0,
  },
  {
    runId: 9,
    status: "success",
    papersProcessed: 18,
    insightsGenerated: 18,
    errorMessage: null,
    startedAt: "2026-04-25T08:00:00Z",
    finishedAt: "2026-04-25T08:03:00Z",
    durationSeconds: 180.0,
  },
  {
    runId: 8,
    status: "failed",
    papersProcessed: 27,
    insightsGenerated: 20,
    errorMessage: "7 insights failed to generate due to missing abstracts.",
    startedAt: "2026-04-26T09:00:00Z",
    finishedAt: "2026-04-26T09:04:00Z",
    durationSeconds: 240.0,
  },
];

const demoEditorialRuns: EditorialRunItem[] = [
  {
    runId: 5,
    status: "success",
    papersProcessed: 4,
    draftsGenerated: 12,
    errorMessage: null,
    startedAt: "2026-04-26T06:10:00Z",
    finishedAt: "2026-04-26T06:20:00Z",
    durationSeconds: 600.0,
  },
  {
    runId: 4,
    status: "success",
    papersProcessed: 3,
    draftsGenerated: 9,
    errorMessage: null,
    startedAt: "2026-04-25T08:10:00Z",
    finishedAt: "2026-04-25T08:18:00Z",
    durationSeconds: 480.0,
  },
  {
    runId: 3,
    status: "failed",
    papersProcessed: 2,
    draftsGenerated: 4,
    errorMessage: "Template rendering failed for bilibili platform.",
    startedAt: "2026-04-24T07:10:00Z",
    finishedAt: "2026-04-24T07:14:00Z",
    durationSeconds: 240.0,
  },
];
