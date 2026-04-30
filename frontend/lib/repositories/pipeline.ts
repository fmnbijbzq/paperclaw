import { runtimeDataSources } from "../data-sources/index.ts";
import type { PipelineDataSource } from "../data-sources/demo/pipeline.ts";
import type {
  CrawlRunItem,
  EditorialRunItem,
  PaperSource,
  PipelineStageItem,
  PipelineTaskCreateInput,
  PipelineTaskItem,
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
  createPipelineTask(input: PipelineTaskCreateInput): Promise<PipelineTaskItem>;
  listPipelineTasks(): Promise<PipelineTaskItem[]>;
  getPipelineTask(taskId: number): Promise<PipelineTaskItem | null>;
  cancelPipelineTask(taskId: number): Promise<PipelineTaskItem>;
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
    async createPipelineTask(input: PipelineTaskCreateInput) {
      return dataSource.createPipelineTask(input);
    },
    async listPipelineTasks() {
      return dataSource.listPipelineTasks();
    },
    async getPipelineTask(taskId: number) {
      return dataSource.getPipelineTask(taskId);
    },
    async cancelPipelineTask(taskId: number) {
      return dataSource.cancelPipelineTask(taskId);
    },
  };
}

export const pipelineRepository = createPipelineRepository(runtimeDataSources.pipeline);
