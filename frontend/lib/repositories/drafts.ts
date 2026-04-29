import { runtimeDataSources } from "../data-sources/index.ts";
import type { DraftsDataSource } from "../data-sources/demo/drafts.ts";
import type {
  DraftActionInput,
  DraftAssignInput,
  DraftDetailItem,
  DraftExportInput,
  DraftListFilters,
  EditorialDraftItem,
  EditorialPlatform,
  ExportRecordItem,
  DraftStatus,
} from "../types.ts";

export interface DraftsRepository {
  listDrafts(filters?: DraftListFilters): Promise<EditorialDraftItem[]>;
  getDraftDetail(draftId: string): Promise<DraftDetailItem | null>;
  reviewDraft(draftId: string, payload: DraftActionInput): Promise<DraftDetailItem>;
  approveDraft(draftId: string, payload: DraftActionInput): Promise<DraftDetailItem>;
  rejectDraft(draftId: string, payload: DraftActionInput): Promise<DraftDetailItem>;
  assignDraft(draftId: string, payload: DraftAssignInput): Promise<DraftDetailItem>;
  exportDraft(draftId: string, payload: DraftExportInput): Promise<ExportRecordItem>;
  getDraftStatusCounts(): Promise<Record<DraftStatus, number>>;
  getDraftPlatformCounts(): Promise<Record<EditorialPlatform, number>>;
}

function compareDesc(left: string, right: string): number {
  return new Date(right).getTime() - new Date(left).getTime();
}

export function createDraftsRepository(dataSource: DraftsDataSource): DraftsRepository {
  async function loadSortedDrafts(): Promise<EditorialDraftItem[]> {
    return [...(await dataSource.listDrafts())].sort((left, right) => compareDesc(left.updatedAt, right.updatedAt));
  }

  return {
    async listDrafts(filters) {
      const drafts = await loadSortedDrafts();
      const statusFilter = filters?.status ?? "all";
      const platformFilter = filters?.platform ?? "all";
      const limit = filters?.limit;

      const filtered = drafts.filter((draft) => {
        const matchesStatus = statusFilter === "all" || draft.status === statusFilter;
        const matchesPlatform = platformFilter === "all" || draft.platform === platformFilter;

        return matchesStatus && matchesPlatform;
      });

      return limit ? filtered.slice(0, limit) : filtered;
    },

    async getDraftDetail(draftId) {
      return dataSource.getDraftDetail(draftId);
    },

    async reviewDraft(draftId, payload) {
      return dataSource.reviewDraft(draftId, payload);
    },

    async approveDraft(draftId, payload) {
      return dataSource.approveDraft(draftId, payload);
    },

    async rejectDraft(draftId, payload) {
      return dataSource.rejectDraft(draftId, payload);
    },

    async assignDraft(draftId, payload) {
      return dataSource.assignDraft(draftId, payload);
    },

    async exportDraft(draftId, payload) {
      return dataSource.exportDraft(draftId, payload);
    },

    async getDraftStatusCounts() {
      const drafts = await loadSortedDrafts();

      const counts: Record<DraftStatus, number> = {
        generated: 0,
        in_review: 0,
        approved: 0,
        rejected: 0,
        exported: 0,
      };

      for (const draft of drafts) {
        counts[draft.status]++;
      }

      return counts;
    },

    async getDraftPlatformCounts() {
      const drafts = await loadSortedDrafts();

      const counts: Record<EditorialPlatform, number> = {
        bilibili: 0,
        xiaohongshu: 0,
        douyin: 0,
      };

      for (const draft of drafts) {
        counts[draft.platform]++;
      }

      return counts;
    },
  };
}

export const draftsRepository = createDraftsRepository(runtimeDataSources.drafts);
