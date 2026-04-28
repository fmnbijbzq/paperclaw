import { demoPapersDataSource, type PapersDataSource } from "../data-sources/demo/papers.ts";
import type { EditorialDraftItem, PaperInsightItem, PaperItem } from "../types.ts";

export interface PaperRepositoryRecord {
  paper: PaperItem;
  insight: PaperInsightItem | null;
  editorialDrafts: EditorialDraftItem[];
}

export interface PapersRepository {
  listPapers(): Promise<PaperItem[]>;
  listEditorialDrafts(): Promise<EditorialDraftItem[]>;
  listRecords(): Promise<PaperRepositoryRecord[]>;
  getRecord(paperId: number): Promise<PaperRepositoryRecord | null>;
  search(query?: string): Promise<PaperRepositoryRecord[]>;
}

function compareDesc(left: string, right: string): number {
  return new Date(right).getTime() - new Date(left).getTime();
}

function buildSearchHaystack(record: PaperRepositoryRecord): string {
  return [
    record.paper.title,
    record.paper.abstract,
    record.paper.source,
    record.paper.venue,
    record.paper.authors.join(" "),
    record.paper.categories.join(" "),
    record.insight?.summaryShort ?? "",
  ]
    .join(" ")
    .toLowerCase();
}

export function createPapersRepository(dataSource: PapersDataSource): PapersRepository {
  async function loadRecords(): Promise<PaperRepositoryRecord[]> {
    const [papers, insights, editorialDrafts] = await Promise.all([
      dataSource.listPapers(),
      dataSource.listInsights(),
      dataSource.listEditorialDrafts(),
    ]);
    const insightMap = new Map(insights.map((insight) => [insight.paperId, insight]));
    const draftsByPaperId = new Map<number, EditorialDraftItem[]>();

    for (const draft of editorialDrafts) {
      const existingDrafts = draftsByPaperId.get(draft.paperId) ?? [];
      existingDrafts.push(draft);
      draftsByPaperId.set(draft.paperId, existingDrafts);
    }

    return [...papers]
      .sort((left, right) => compareDesc(left.publishedAt, right.publishedAt))
      .map((paper) => ({
        paper,
        insight: insightMap.get(paper.paperId) ?? null,
        editorialDrafts: [...(draftsByPaperId.get(paper.paperId) ?? [])].sort((left, right) =>
          compareDesc(left.updatedAt, right.updatedAt),
        ),
      }));
  }

  return {
    async listPapers() {
      return [...(await dataSource.listPapers())].sort((left, right) => compareDesc(left.publishedAt, right.publishedAt));
    },
    async listEditorialDrafts() {
      return [...(await dataSource.listEditorialDrafts())].sort((left, right) => compareDesc(left.updatedAt, right.updatedAt));
    },
    async listRecords() {
      return loadRecords();
    },
    async getRecord(paperId: number) {
      const records = await loadRecords();

      return records.find((record) => record.paper.paperId === paperId) ?? null;
    },
    async search(query = "") {
      const normalizedQuery = query.trim().toLowerCase();

      if (!normalizedQuery) {
        return loadRecords();
      }

      const records = await loadRecords();

      return records.filter((record) => buildSearchHaystack(record).includes(normalizedQuery));
    },
  };
}

export const papersRepository = createPapersRepository(demoPapersDataSource);
