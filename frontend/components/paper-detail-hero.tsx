import { ArrowUpRight, BellRing, BrainCircuit, FileText, FileUp, Microscope } from "lucide-react";

import { formatFullDate, formatSource } from "@/lib/format";
import type { PaperRecord } from "@/lib/types";
import { StatusBadge } from "@/components/status-badge";

interface PaperDetailHeroProps {
  record: PaperRecord;
}

export function PaperDetailHero({ record }: PaperDetailHeroProps) {
  return (
    <section className="panel-card rounded-[2rem] p-6 sm:p-7">
      <div className="flex flex-col gap-6 xl:flex-row xl:items-start xl:justify-between">
        <div className="max-w-4xl">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge label={formatSource(record.paper.source)} tone="info" />
            <StatusBadge label={record.insight ? "Insight ready" : "Insight pending"} tone={record.insight ? "success" : "neutral"} />
            <StatusBadge
              label={record.notifications[0]?.success ? "Delivered to Feishu" : record.notifications[0] ? "Retry pending" : "Not sent yet"}
              tone={record.notifications[0]?.success ? "success" : record.notifications[0] ? "danger" : "warning"}
            />
          </div>
          <h1 className="section-title mt-5 text-4xl font-semibold text-white sm:text-5xl">{record.paper.title}</h1>
          <p className="mt-4 max-w-3xl text-base subtle-copy">{record.paper.abstract}</p>
          <p className="mt-5 text-sm text-slate-200">{record.paper.authors.join(", ")}</p>
          <dl className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-2xl border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.55)] p-4">
              <dt className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--accent-blue)]">
                <Microscope className="h-4 w-4" aria-hidden="true" />
                Venue
              </dt>
              <dd className="mt-2 text-sm text-white">{record.paper.venue}</dd>
            </div>
            <div className="rounded-2xl border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.55)] p-4">
              <dt className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--accent-blue)]">
                <FileText className="h-4 w-4" aria-hidden="true" />
                Published
              </dt>
              <dd className="mt-2 text-sm text-white">{formatFullDate(record.paper.publishedAt)}</dd>
            </div>
            <div className="rounded-2xl border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.55)] p-4">
              <dt className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--accent-blue)]">
                <BrainCircuit className="h-4 w-4" aria-hidden="true" />
                Confidence
              </dt>
              <dd className="mt-2 text-sm text-white">
                {record.insight ? `${Math.round(record.insight.confidenceScore * 100)}% confidence` : "Insight not generated"}
              </dd>
            </div>
            <div className="rounded-2xl border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.55)] p-4">
              <dt className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--accent-blue)]">
                <BellRing className="h-4 w-4" aria-hidden="true" />
                Drafts
              </dt>
              <dd className="mt-2 text-sm text-white">{record.editorialDrafts.length} platform artifacts</dd>
            </div>
          </dl>
        </div>

        <div className="flex flex-col gap-3 xl:w-72">
          <a href={record.paper.paperUrl} target="_blank" rel="noreferrer" className="action-button action-button-primary">
            Open abstract
            <ArrowUpRight className="h-4 w-4" aria-hidden="true" />
          </a>
          <a href={record.paper.pdfUrl} target="_blank" rel="noreferrer" className="action-button action-button-secondary">
            Open PDF
            <FileUp className="h-4 w-4" aria-hidden="true" />
          </a>
          <div className="rounded-[1.5rem] border border-[rgba(245,158,11,0.18)] bg-[rgba(245,158,11,0.08)] p-4">
            <p className="text-sm font-semibold text-white">Editorial readiness</p>
            <p className="mt-2 text-sm subtle-copy">
              {record.editorialDrafts.length > 0
                ? "Draft artifacts exist. Remaining work is review, export, and reliable downstream notification."
                : "No draft artifacts are generated for this paper yet."}
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
