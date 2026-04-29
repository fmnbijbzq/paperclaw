import { runtimeDataSources } from "../data-sources/index.ts";
import type { PipelineDataSource } from "../data-sources/demo/pipeline.ts";
import type {
  CrawlRunItem,
  EditorialRunItem,
  PaperSource,
  PipelineStageItem,
  SourceHealthItem,
  SummarizationRunItem,
} from "../types.ts";

export interface PipelineRepository {
  listStages(): Promise<PipelineStageItem[]>;
  listSourceHealth(): Promise<SourceHealthItem[]>;
  getSourceHealthBySource(source: PaperSource): Promise<SourceHealthItem | null>;
  listCrawlRuns(): Promise<CrawlRunItem[]>;
  listSummarizationRuns(): Promise<SummarizationRunItem[]>;
  listEditorialRuns(): Promise<EditorialRunItem[]>;
}

export function createPipelineRepository(dataSource: PipelineDataSource): PipelineRepository {
  return {
    async listStages() {
      return dataSource.listPipelineStages();
    },
    async listSourceHealth() {
      return dataSource.listSourceHealth();
    },
    async getSourceHealthBySource(source: PaperSource) {
      const sourceHealth = await dataSource.listSourceHealth();

      return sourceHealth.find((item) => item.source === source) ?? null;
    },
    async listCrawlRuns() {
      return dataSource.listCrawlRuns();
    },
    async listSummarizationRuns() {
      return dataSource.listSummarizationRuns();
    },
    async listEditorialRuns() {
      return dataSource.listEditorialRuns();
    },
  };
}

export const pipelineRepository = createPipelineRepository(runtimeDataSources.pipeline);
