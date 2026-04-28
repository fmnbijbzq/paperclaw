import { demoPipelineDataSource, type PipelineDataSource } from "../data-sources/demo/pipeline.ts";
import type { PaperSource, PipelineStageItem, SourceHealthItem } from "../types.ts";

export interface PipelineRepository {
  listStages(): Promise<PipelineStageItem[]>;
  listSourceHealth(): Promise<SourceHealthItem[]>;
  getSourceHealthBySource(source: PaperSource): Promise<SourceHealthItem | null>;
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
  };
}

export const pipelineRepository = createPipelineRepository(demoPipelineDataSource);
