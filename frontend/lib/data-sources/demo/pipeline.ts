import { pipelineStages, sourceHealth } from "../../demo-data.ts";
import type { PipelineStageItem, SourceHealthItem } from "../../types.ts";

export interface PipelineDataSource {
  listPipelineStages(): Promise<PipelineStageItem[]>;
  listSourceHealth(): Promise<SourceHealthItem[]>;
}

export const demoPipelineDataSource: PipelineDataSource = {
  async listPipelineStages() {
    return [...pipelineStages];
  },
  async listSourceHealth() {
    return [...sourceHealth];
  },
};
