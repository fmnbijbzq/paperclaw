import { runtimeDataSources } from "../data-sources/index.ts";
import type { PapersDataSource } from "../data-sources/demo/papers.ts";
import type { EditorialDraftItem, PaperInsightItem, PaperItem, PaperSearchParams } from "../types.ts";

export interface PaperRepositoryRecord {
  paper: PaperItem;
  insight: PaperInsightItem | null;
  editorialDrafts: EditorialDraftItem[];
}

export interface PaperRepositorySearchResult {
  records: PaperRepositoryRecord[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
  appliedQuery: string;
}

export interface PapersRepository {
  listPapers(): Promise<PaperItem[]>;
  listEditorialDrafts(): Promise<EditorialDraftItem[]>;
  listRecords(): Promise<PaperRepositoryRecord[]>;
  getRecord(paperId: number): Promise<PaperRepositoryRecord | null>;
  search(params?: PaperSearchParams | string): Promise<PaperRepositorySearchResult>;
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
    const [papersList, insights, editorialDrafts] = await Promise.all([
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

    return [...papersList]
      .sort((left, right) => compareDesc(left.publishedAt, right.publishedAt))
      .map((paper) => ({
        paper,
        insight: insightMap.get(paper.paperId) ?? null,
        editorialDrafts: [...(draftsByPaperId.get(paper.paperId) ?? [])].sort((left, right) =>
          compareDesc(left.updatedAt, right.updatedAt),
        ),
      }));
  }

  async function enrichPaperItems(papersList: PaperItem[]): Promise<PaperRepositoryRecord[]> {
    const allRecords = await loadRecords();
    const recordMap = new Map(allRecords.map((record) => [record.paper.paperId, record]));

    return papersList.map((paper) => {
      const existing = recordMap.get(paper.paperId);

      return existing ?? {
        paper,
        insight: null,
        editorialDrafts: [],
      };
    });
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
    async search(params: PaperSearchParams | string = {}) {
      const normalizedParams: PaperSearchParams = typeof params === "string" ? { q: params } : params;
      const normalizedQuery = (normalizedParams.q ?? "").trim().toLowerCase();
      const source = normalizedParams.source ?? "all";
      const category = normalizedParams.category;
      const venue = normalizedParams.venue;
      const hasInsight = normalizedParams.hasInsight;
      const hasDraft = normalizedParams.hasDraft;
      const page = normalizedParams.page ?? 1;
      const pageSize = normalizedParams.pageSize ?? 20;

      // If the data source supports server-side search, use it
      if (dataSource.searchPapers) {
        const result = await dataSource.searchPapers(normalizedParams);
        const records = await enrichPaperItems(result.items);

        let filtered = records;

        // Apply additional client-side filters that the API might not support
        if (hasInsight !== undefined) {
          filtered = filtered.filter((record) => (hasInsight ? !!record.insight : !record.insight));
        }

        if (hasDraft !== undefined) {
          filtered = filtered.filter((record) =>
            hasDraft ? record.editorialDrafts.length > 0 : record.editorialDrafts.length === 0,
          );
        }

        const total = filtered.length;
        const totalPages = Math.ceil(total / pageSize);

        return {
          records: filtered,
          total,
          page,
          pageSize,
          totalPages,
          appliedQuery: normalizedParams.q ?? "",
        };
      }

      // Fallback to client-side search
      let records = await loadRecords();

      // Text search
      if (normalizedQuery) {
        records = records.filter((record) => buildSearchHaystack(record).includes(normalizedQuery));
      }

      // Source filter
      if (source && source !== "all") {
        records = records.filter((record) => record.paper.source === source);
      }

      // Category filter
      if (category) {
        const lowerCategory = category.toLowerCase();
        records = records.filter((record) =>
          record.paper.categories.some((cat) => cat.toLowerCase().includes(lowerCategory)),
        );
      }

      // Venue filter
      if (venue) {
        const lowerVenue = venue.toLowerCase();
        records = records.filter((record) => record.paper.venue.toLowerCase().includes(lowerVenue));
      }

      // Has insight filter
      if (hasInsight !== undefined) {
        records = records.filter((record) => (hasInsight ? !!record.insight : !record.insight));
      }

      // Has draft filter
      if (hasDraft !== undefined) {
        records = records.filter((record) =>
          hasDraft ? record.editorialDrafts.length > 0 : record.editorialDrafts.length === 0,
        );
      }

      const total = records.length;
      const totalPages = Math.ceil(total / pageSize);
      const offset = (page - 1) * pageSize;
      const paginatedRecords = records.slice(offset, offset + pageSize);

      return {
        records: paginatedRecords,
        total,
        page,
        pageSize,
        totalPages,
        appliedQuery: normalizedParams.q ?? "",
      };
    },
  };
}

export const papersRepository = createPapersRepository(runtimeDataSources.papers);
