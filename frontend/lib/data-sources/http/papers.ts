import type { EditorialDraftsResponse, PaperInsightsResponse, PapersListResponse } from "../../api-contracts.ts";
import { createHttpClient, type HttpDataSourceOptions } from "./shared.ts";
import type { PapersDataSource } from "../demo/papers.ts";

export function createHttpPapersDataSource(options: HttpDataSourceOptions): PapersDataSource {
  const client = createHttpClient(options);

  return {
    async listPapers() {
      const response = await client.get<PapersListResponse>("papers");

      return response.items.map((item) => item.paper);
    },
    async listInsights() {
      const response = await client.get<PaperInsightsResponse>("papers/insights");

      return [...response.items];
    },
    async listEditorialDrafts() {
      const response = await client.get<EditorialDraftsResponse>("papers/editorial-drafts");

      return [...response.items];
    },
  };
}
