import Link from "next/link";
import { ArrowUpRight, BellRing, BrainCircuit, FilePenLine } from "lucide-react";

import { formatDate, formatSource } from "@/lib/format";
import type { PaperRecord } from "@/lib/types";
import { StatusBadge } from "@/components/status-badge";

function getDeliveryTone(record: PaperRecord) {
  const latest = record.notifications[0];

  if (!latest) {
    return { label: "Pending send", tone: "warning" as const };
  }

  return latest.success
    ? { label: "Delivered", tone: "success" as const }
    : { label: "Retry needed", tone: "danger" as const };
}

interface PaperListProps {
  records: PaperRecord[];
}

export function PaperList({ records }: PaperListProps) {
  return (
    <ul className="space-y-4">
      {records.map((record) => {
        const delivery = getDeliveryTone(record);

        return (
          <li key={record.paper.paperId}>
            <Link
              href={`/papers/${record.paper.paperId}`}
              className="panel-card panel-card-interactive block rounded-[1.5rem] p-5"
            >
              <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge label={formatSource(record.paper.source)} tone="info" />
                    <StatusBadge label={delivery.label} tone={delivery.tone} />
                    <StatusBadge label={record.insight ? "Insight attached" : "Awaiting insight"} tone={record.insight ? "success" : "neutral"} />
                  </div>
                  <h3 className="mt-4 text-xl font-semibold text-white">{record.paper.title}</h3>
                  <p className="mt-2 text-sm subtle-copy">{record.paper.authors.join(", ")}</p>
                  <p className="mt-3 text-sm subtle-copy">
                    {record.insight?.summaryShort ?? "Paper metadata is stored; insight generation has not completed yet."}
                  </p>
                  <div className="mt-4 flex flex-wrap gap-2 text-xs">
                    {record.paper.categories.map((category) => (
                      <span
                        key={category}
                        className="rounded-full border border-[color:var(--border-subtle)] bg-[rgba(15,23,42,0.6)] px-3 py-1 font-medium text-slate-200"
                      >
                        {category}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="grid gap-3 sm:grid-cols-3 xl:w-[24rem]">
                  <div className="rounded-2xl border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.55)] p-3">
                    <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--accent-blue)]">
                      <BrainCircuit className="h-4 w-4" aria-hidden="true" />
                      Insight
                    </p>
                    <p className="mt-3 text-sm text-white">
                      {record.insight ? `${Math.round(record.insight.confidenceScore * 100)}% confidence` : "Not generated"}
                    </p>
                  </div>
                  <div className="rounded-2xl border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.55)] p-3">
                    <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--accent-amber)]">
                      <FilePenLine className="h-4 w-4" aria-hidden="true" />
                      Drafts
                    </p>
                    <p className="mt-3 text-sm text-white">{record.editorialDrafts.length} artifacts</p>
                  </div>
                  <div className="rounded-2xl border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.55)] p-3">
                    <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--accent-blue)]">
                      <BellRing className="h-4 w-4" aria-hidden="true" />
                      Published
                    </p>
                    <p className="mt-3 text-sm text-white">{formatDate(record.paper.publishedAt)}</p>
                  </div>
                </div>
              </div>
              <div className="mt-4 flex items-center justify-between border-t border-[color:rgba(115,147,197,0.18)] pt-4 text-sm">
                <span className="subtle-copy">
                  {record.paper.venue} · {record.paper.paperUrl}
                </span>
                <span className="inline-flex items-center gap-2 font-semibold text-white">
                  Open detail
                  <ArrowUpRight className="h-4 w-4 text-[color:var(--accent-amber)]" aria-hidden="true" />
                </span>
              </div>
            </Link>
          </li>
        );
      })}
    </ul>
  );
}
