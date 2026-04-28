import type { PipelineSummaryResponse } from "../../api-contracts.ts";
import { createHttpClient, type HttpDataSourceOptions } from "./shared.ts";
import type { PipelineDataSource } from "../demo/pipeline.ts";

export function createHttpPipelineDataSource(options: HttpDataSourceOptions): PipelineDataSource {
  const client = createHttpClient(options);

  async function loadSummary(): Promise<PipelineSummaryResponse> {
    return client.get<PipelineSummaryResponse>("pipeline/summary");
  }

  return {
    async listPipelineStages() {
      return (await loadSummary()).stages;
    },
    async listSourceHealth() {
      return (await loadSummary()).sourceHealth;
    },
  };
}
