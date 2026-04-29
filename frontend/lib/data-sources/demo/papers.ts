import { editorialDrafts, insights, papers } from "../../demo-data.ts";
import type { EditorialDraftItem, PaperInsightItem, PaperItem, PaperSearchParams } from "../../types.ts";

export interface PapersDataSourceSearchResult {
  items: PaperItem[];
  total: number;
}

export interface PapersDataSource {
  listPapers(): Promise<PaperItem[]>;
  listInsights(): Promise<PaperInsightItem[]>;
  listEditorialDrafts(): Promise<EditorialDraftItem[]>;
  searchPapers?(params: PaperSearchParams): Promise<PapersDataSourceSearchResult>;
}

export const demoPapersDataSource: PapersDataSource = {
  async listPapers() {
    return [...papers];
  },
  async listInsights() {
    return [...insights];
  },
  async listEditorialDrafts() {
    return [...editorialDrafts];
  },
};
