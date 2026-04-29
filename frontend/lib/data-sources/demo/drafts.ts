import {
  editorialDraftContent,
  editorialDraftReviewNotes,
  editorialDrafts,
  papers,
} from "../../demo-data.ts";
import type {
  DraftActionInput,
  DraftAssignInput,
  DraftDetailItem,
  DraftExportInput,
  DraftListFilters,
  DraftStatus,
  EditorialDraftItem,
  EditorialPlatform,
  ExportRecordItem,
  PaperItem,
} from "../../types.ts";

export interface DraftsDataSource {
  listDrafts(filters?: DraftListFilters): Promise<EditorialDraftItem[]>;
  getDraftDetail(draftId: string): Promise<DraftDetailItem | null>;
  reviewDraft(draftId: string, payload: DraftActionInput): Promise<DraftDetailItem>;
  approveDraft(draftId: string, payload: DraftActionInput): Promise<DraftDetailItem>;
  rejectDraft(draftId: string, payload: DraftActionInput): Promise<DraftDetailItem>;
  assignDraft(draftId: string, payload: DraftAssignInput): Promise<DraftDetailItem>;
  exportDraft(draftId: string, payload: DraftExportInput): Promise<ExportRecordItem>;
  listPapers(): Promise<PaperItem[]>;
}

function matchesStatus(draft: EditorialDraftItem, status: DraftStatus | "all"): boolean {
  return status === "all" || draft.status === status;
}

function matchesPlatform(draft: EditorialDraftItem, platform: EditorialPlatform | "all"): boolean {
  return platform === "all" || draft.platform === platform;
}

function getDraftPaper(draft: EditorialDraftItem): PaperItem {
  return papers.find((item) => item.paperId === draft.paperId)!;
}

function buildDetail(draftId: string, draft: EditorialDraftItem, overrides?: Partial<DraftDetailItem>): DraftDetailItem {
  return {
    ...draft,
    markdownContent: overrides?.markdownContent ?? editorialDraftContent[draftId] ?? "",
    reviewNote: overrides?.reviewNote ?? editorialDraftReviewNotes[draftId] ?? null,
    paper: overrides?.paper ?? getDraftPaper(draft),
    ...overrides,
  };
}

export const demoDraftsDataSource: DraftsDataSource = {
  async listDrafts(filters) {
    const statusFilter = filters?.status ?? "all";
    const platformFilter = filters?.platform ?? "all";
    const limit = filters?.limit;

    const filtered = editorialDrafts.filter(
      (draft) => matchesStatus(draft, statusFilter) && matchesPlatform(draft, platformFilter),
    );

    return limit ? filtered.slice(0, limit) : [...filtered];
  },

  async getDraftDetail(draftId) {
    const draft = editorialDrafts.find((item) => item.draftId === draftId);

    if (!draft) {
      return null;
    }

    return buildDetail(draftId, draft);
  },

  async reviewDraft(draftId, payload) {
    const draft = editorialDrafts.find((item) => item.draftId === draftId) ?? editorialDrafts[0];

    return buildDetail(draftId, draft, {
      status: "in_review",
      reviewNote: payload.note ?? null,
      updatedAt: new Date().toISOString(),
    });
  },

  async approveDraft(draftId, payload) {
    const draft = editorialDrafts.find((item) => item.draftId === draftId) ?? editorialDrafts[0];

    return buildDetail(draftId, draft, {
      status: "approved",
      reviewNote: payload.note ?? null,
      updatedAt: new Date().toISOString(),
    });
  },

  async rejectDraft(draftId, payload) {
    const draft = editorialDrafts.find((item) => item.draftId === draftId) ?? editorialDrafts[0];

    return buildDetail(draftId, draft, {
      status: "rejected",
      reviewNote: payload.note ?? null,
      updatedAt: new Date().toISOString(),
    });
  },

  async assignDraft(draftId, payload) {
    const draft = editorialDrafts.find((item) => item.draftId === draftId) ?? editorialDrafts[0];

    return buildDetail(draftId, draft, {
      assignee: payload.assignee,
      updatedAt: new Date().toISOString(),
    });
  },

  async exportDraft(draftId, payload) {
    return {
      exportId: Date.now(),
      draftId,
      exportedBy: payload.exportedBy,
      success: true,
      sourcePath: `outputs/${draftId}.md`,
      destinationPath: `outputs/exported/${draftId}.md`,
      errorMessage: null,
      createdAt: new Date().toISOString(),
    };
  },

  async listPapers() {
    return [...papers];
  },
};
