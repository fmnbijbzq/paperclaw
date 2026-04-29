import { runtimeDataSources } from "../data-sources/index.ts";
import type { ExportsDataSource } from "../data-sources/demo/exports.ts";
import type { ExportRecordItem } from "../types.ts";

export interface ExportsRepository {
  listExportRecords(): Promise<ExportRecordItem[]>;
}

function compareDesc(left: string, right: string): number {
  return new Date(right).getTime() - new Date(left).getTime();
}

export function createExportsRepository(dataSource: ExportsDataSource): ExportsRepository {
  return {
    async listExportRecords() {
      return [...(await dataSource.listExportRecords())].sort((left, right) => compareDesc(left.createdAt, right.createdAt));
    },
  };
}

export const exportsRepository = createExportsRepository(runtimeDataSources.exports);
