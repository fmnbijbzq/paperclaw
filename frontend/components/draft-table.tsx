import Link from "next/link";

import { formatDateTime, formatDraftStatus, formatPlatform } from "@/lib/format";
import type { DraftStatus, EditorialDraftItem } from "@/lib/types";
import { StatusBadge } from "@/components/status-badge";

function getDraftStatusTone(status: DraftStatus): "success" | "warning" | "danger" | "info" | "neutral" {
  const toneMap: Record<DraftStatus, "success" | "warning" | "danger" | "info" | "neutral"> = {
    generated: "neutral",
    in_review: "warning",
    approved: "success",
    rejected: "danger",
    exported: "info",
  };

  return toneMap[status];
}

interface DraftTableProps {
  drafts: EditorialDraftItem[];
}

export function DraftTable({ drafts }: DraftTableProps) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full border-separate border-spacing-y-3">
        <caption className="sr-only">Editorial drafts across platforms</caption>
        <thead>
          <tr className="text-left text-xs font-semibold uppercase tracking-[0.18em] text-[color:var(--text-dim)]">
            <th scope="col" className="px-4 py-2">
              Title
            </th>
            <th scope="col" className="px-4 py-2">
              Platform
            </th>
            <th scope="col" className="px-4 py-2">
              Status
            </th>
            <th scope="col" className="px-4 py-2">
              Assignee
            </th>
            <th scope="col" className="px-4 py-2">
              Updated
            </th>
          </tr>
        </thead>
        <tbody>
          {drafts.map((draft) => (
            <tr key={draft.draftId} className="panel-card rounded-[1.2rem] align-top">
              <td className="rounded-l-[1.2rem] px-4 py-4">
                <Link href={`/drafts/${draft.draftId}`} className="font-semibold text-white">
                  {draft.title}
                </Link>
                <p className="mt-1 text-xs subtle-copy line-clamp-1">{draft.hook}</p>
              </td>
              <td className="px-4 py-4">
                <StatusBadge label={formatPlatform(draft.platform)} tone="info" />
              </td>
              <td className="px-4 py-4">
                <StatusBadge label={formatDraftStatus(draft.status)} tone={getDraftStatusTone(draft.status)} />
              </td>
              <td className="px-4 py-4 text-sm text-white">
                {draft.assignee ?? <span className="subtle-copy">Unassigned</span>}
              </td>
              <td className="rounded-r-[1.2rem] px-4 py-4 text-sm subtle-copy">{formatDateTime(draft.updatedAt)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
