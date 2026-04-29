import type { ExportRecordsResponse } from "../../api-contracts.ts";
import { createHttpClient, type HttpDataSourceOptions } from "./shared.ts";
import type { ExportsDataSource } from "../demo/exports.ts";

export function createHttpExportsDataSource(options: HttpDataSourceOptions): ExportsDataSource {
  const client = createHttpClient(options);

  return {
    async listExportRecords() {
      const response = await client.get<ExportRecordsResponse>("exports");

      return [...response.items];
    },
  };
}
