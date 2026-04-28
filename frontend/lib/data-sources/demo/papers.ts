import { editorialDrafts, insights, papers } from "../../demo-data.ts";
import type { EditorialDraftItem, PaperInsightItem, PaperItem } from "../../types.ts";

export interface PapersDataSource {
  listPapers(): Promise<PaperItem[]>;
  listInsights(): Promise<PaperInsightItem[]>;
  listEditorialDrafts(): Promise<EditorialDraftItem[]>;
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
