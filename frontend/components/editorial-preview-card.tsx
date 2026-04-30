import { FileText, FolderGit2 } from "lucide-react";

import { StatusBadge } from "@/components/status-badge";
import { formatDateTime, formatDraftStatus, formatPlatform } from "@/lib/format";
import type { DraftStatus, EditorialDraftItem } from "@/lib/types";

const toneMap: Record<DraftStatus, "success" | "warning" | "danger" | "info" | "neutral"> = {
  generated: "neutral",
  in_review: "warning",
  approved: "success",
  rejected: "danger",
  exported: "info",
};

interface EditorialPreviewCardProps {
  draft: EditorialDraftItem;
}

export function EditorialPreviewCard({ draft }: EditorialPreviewCardProps) {
  return (
    <article className="panel-card rounded-[1.4rem] p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="eyebrow">{formatPlatform(draft.platform)}</p>
          <h3 className="mt-2 text-base font-semibold text-white">{draft.title}</h3>
        </div>
        <StatusBadge label={formatDraftStatus(draft.status)} tone={toneMap[draft.status]} />
      </div>
      <p className="mt-3 text-sm subtle-copy">{draft.hook}</p>
      <dl className="mt-4 space-y-3 text-sm">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-[color:var(--accent-blue)]" aria-hidden="true" />
          <div>
            <dt className="subtle-copy">更新时间</dt>
            <dd className="text-white">{formatDateTime(draft.updatedAt)}</dd>
          </div>
        </div>
        <div className="flex items-start gap-2">
          <FolderGit2 className="mt-0.5 h-4 w-4 text-[color:var(--accent-amber)]" aria-hidden="true" />
          <div className="min-w-0">
            <dt className="subtle-copy">输出路径</dt>
            <dd className="truncate text-white">{draft.outputPath}</dd>
          </div>
        </div>
      </dl>
    </article>
  );
}
