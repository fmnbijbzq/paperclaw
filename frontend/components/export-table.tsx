import Link from "next/link";

import { formatDateTime, formatDraftStatus, formatPlatform } from "@/lib/format";
import type { ExportFeedRow } from "@/lib/types";
import { StatusBadge } from "@/components/status-badge";

interface ExportTableProps {
  rows: ExportFeedRow[];
}

export function ExportTable({ rows }: ExportTableProps) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full border-separate border-spacing-y-3">
        <caption className="sr-only">Export history records</caption>
        <thead>
          <tr className="text-left text-xs font-semibold uppercase tracking-[0.18em] text-[color:var(--text-dim)]">
            <th scope="col" className="px-4 py-2">
              Draft
            </th>
            <th scope="col" className="px-4 py-2">
              Platform
            </th>
            <th scope="col" className="px-4 py-2">
              Status
            </th>
            <th scope="col" className="px-4 py-2">
              Exported By
            </th>
            <th scope="col" className="px-4 py-2">
              Result
            </th>
            <th scope="col" className="px-4 py-2">
              Time
            </th>
            <th scope="col" className="px-4 py-2">
              Error
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ record, draftTitle, platform, draftStatus }) => (
            <tr key={record.exportId} className="panel-card rounded-[1.2rem] align-top">
              <td className="rounded-l-[1.2rem] px-4 py-4">
                <Link href={`/drafts/${record.draftId}`} className="font-semibold text-white">
                  {draftTitle}
                </Link>
                <p className="mt-1 text-xs subtle-copy">ID: {record.draftId}</p>
              </td>
              <td className="px-4 py-4">
                {platform ? <StatusBadge label={formatPlatform(platform)} tone="info" /> : <span className="text-sm subtle-copy">—</span>}
              </td>
              <td className="px-4 py-4">
                {draftStatus ? <StatusBadge label={formatDraftStatus(draftStatus)} tone="neutral" /> : <span className="text-sm subtle-copy">—</span>}
              </td>
              <td className="px-4 py-4 text-sm text-white">{record.exportedBy}</td>
              <td className="px-4 py-4">
                <StatusBadge label={record.success ? "Success" : "Failed"} tone={record.success ? "success" : "danger"} />
              </td>
              <td className="px-4 py-4 text-sm subtle-copy">{formatDateTime(record.createdAt)}</td>
              <td className="rounded-r-[1.2rem] px-4 py-4 text-sm subtle-copy">
                {record.errorMessage ?? "No error recorded"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
