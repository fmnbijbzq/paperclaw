import type { EditorialDraftsResponse, PaperInsightsResponse, PapersListResponse } from "../../api-contracts.ts";
import type { PaperSearchParams } from "../../types.ts";
import { createHttpClient, type HttpDataSourceOptions, type HttpQueryParams } from "./shared.ts";
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
    async searchPapers(params: PaperSearchParams) {
      const query: HttpQueryParams = {};

      if (params.q) {
        query.q = params.q;
      }

      if (params.source && params.source !== "all") {
        query.source = params.source;
      }

      if (params.category) {
        query.category = params.category;
      }

      if (params.venue) {
        query.venue = params.venue;
      }

      if (params.hasInsight !== undefined) {
        query.hasInsight = params.hasInsight;
      }

      if (params.hasDraft !== undefined) {
        query.hasDraft = params.hasDraft;
      }

      if (params.page && params.pageSize) {
        query.limit = params.pageSize;
        query.offset = (params.page - 1) * params.pageSize;
      }

      const response = await client.get<PapersListResponse>("papers", query);

      return {
        items: response.items.map((item) => item.paper),
        total: response.total,
      };
    },
  };
}
