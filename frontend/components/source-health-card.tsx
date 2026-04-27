import { Activity, DatabaseZap, Waves } from "lucide-react";

import { formatDateTime, formatSource } from "@/lib/format";
import type { SourceHealthItem } from "@/lib/types";
import { StatusBadge } from "@/components/status-badge";

const toneMap = {
  healthy: "success",
  degraded: "danger",
  attention: "warning",
} as const;

interface SourceHealthCardProps {
  item: SourceHealthItem;
}

export function SourceHealthCard({ item }: SourceHealthCardProps) {
  return (
    <article className="panel-card rounded-[1.4rem] p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-white">{formatSource(item.source)}</h3>
          <p className="mt-1 text-xs subtle-copy">Last run {formatDateTime(item.lastRunAt)}</p>
        </div>
        <StatusBadge label={item.status} tone={toneMap[item.status]} />
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <div className="rounded-2xl border border-[color:var(--border-subtle)] bg-[rgba(15,23,42,0.6)] p-3">
          <dt className="flex items-center gap-2 subtle-copy">
            <Waves className="h-4 w-4 text-[color:var(--accent-blue)]" aria-hidden="true" />
            Fetched
          </dt>
          <dd className="mt-2 text-lg font-semibold text-white">{item.fetchedCount}</dd>
        </div>
        <div className="rounded-2xl border border-[color:var(--border-subtle)] bg-[rgba(15,23,42,0.6)] p-3">
          <dt className="flex items-center gap-2 subtle-copy">
            <DatabaseZap className="h-4 w-4 text-[color:var(--accent-amber)]" aria-hidden="true" />
            New
          </dt>
          <dd className="mt-2 text-lg font-semibold text-white">{item.newCount}</dd>
        </div>
      </dl>
      <p className="mt-4 flex items-start gap-2 text-sm subtle-copy">
        <Activity className="mt-0.5 h-4 w-4 shrink-0 text-[color:var(--accent-blue)]" aria-hidden="true" />
        <span>{item.notes}</span>
      </p>
    </article>
  );
}
