import type {
  CrawlRunsResponse,
  EditorialRunsResponse,
  PipelineSummaryResponse,
  SummarizationRunsResponse,
} from "../../api-contracts.ts";
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
    async listCrawlRuns() {
      const response = await client.get<CrawlRunsResponse>("pipeline/runs/crawl");
      return response.items;
    },
    async listSummarizationRuns() {
      const response = await client.get<SummarizationRunsResponse>("pipeline/runs/summarization");
      return response.items;
    },
    async listEditorialRuns() {
      const response = await client.get<EditorialRunsResponse>("pipeline/runs/editorial");
      return response.items;
    },
  };
}
