import type {
  EditorialDraftDetailResponse,
  EditorialDraftsResponse,
} from "../../api-contracts.ts";
import type {
  DraftActionInput,
  DraftAssignInput,
  DraftDetailItem,
  DraftExportInput,
  DraftListFilters,
  ExportRecordItem,
} from "../../types.ts";
import { createHttpClient, type HttpDataSourceOptions, type HttpQueryParams } from "./shared.ts";
import type { DraftsDataSource } from "../demo/drafts.ts";

export function createHttpDraftsDataSource(options: HttpDataSourceOptions): DraftsDataSource {
  const client = createHttpClient(options);

  async function postAction<T>(path: string, body: unknown): Promise<T> {
    const requestUrl = client.buildUrl(path);
    const fetchImpl = options.fetch ?? fetch;
    const response = await fetchImpl(requestUrl, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        accept: "application/json",
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      throw new Error(`HTTP request failed with status ${response.status} for ${requestUrl}`);
    }

    const envelope = (await response.json()) as { data: T; meta: unknown };

    return envelope.data;
  }

  return {
    async listDrafts(filters?: DraftListFilters) {
      const query: HttpQueryParams = {};

      if (filters?.status && filters.status !== "all") {
        query.status = filters.status;
      }

      if (filters?.platform && filters.platform !== "all") {
        query.platform = filters.platform;
      }

      if (filters?.limit) {
        query.limit = filters.limit;
      }

      const response = await client.get<EditorialDraftsResponse>("drafts", query);

      return [...response.items];
    },

    async getDraftDetail(draftId: string) {
      try {
        return await client.get<EditorialDraftDetailResponse>(`drafts/${draftId}`);
      } catch {
        return null;
      }
    },

    async reviewDraft(draftId: string, payload: DraftActionInput) {
      return postAction<DraftDetailItem>(`drafts/${draftId}/review`, payload);
    },

    async approveDraft(draftId: string, payload: DraftActionInput) {
      return postAction<DraftDetailItem>(`drafts/${draftId}/approve`, payload);
    },

    async rejectDraft(draftId: string, payload: DraftActionInput) {
      return postAction<DraftDetailItem>(`drafts/${draftId}/reject`, payload);
    },

    async assignDraft(draftId: string, payload: DraftAssignInput) {
      return postAction<DraftDetailItem>(`drafts/${draftId}/assign`, payload);
    },

    async exportDraft(draftId: string, payload: DraftExportInput) {
      return postAction<ExportRecordItem>(`drafts/${draftId}/export`, payload);
    },

    async listPapers() {
      return [];
    },
  };
}
