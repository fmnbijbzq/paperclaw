import { exportRecords } from "../../demo-data.ts";
import type { ExportRecordItem } from "../../types.ts";

export interface ExportsDataSource {
  listExportRecords(): Promise<ExportRecordItem[]>;
}

export const demoExportsDataSource: ExportsDataSource = {
  async listExportRecords() {
    return [...exportRecords];
  },
};
