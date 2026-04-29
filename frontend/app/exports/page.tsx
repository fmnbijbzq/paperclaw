import { ArrowDownToLine, CheckCircle2, XCircle } from "lucide-react";

import { EmptyState } from "@/components/empty-state";
import { ExportTable } from "@/components/export-table";
import { SectionCard } from "@/components/section-card";
import { getExportRecords } from "@/lib/queries";

export default async function ExportsPage() {
  const rows = await getExportRecords();

  const successful = rows.filter((row) => row.record.success).length;
  const failed = rows.length - successful;

  return (
    <div className="space-y-6 lg:space-y-8">
      <section className="panel-card rounded-[2rem] px-6 py-7 sm:px-8 sm:py-9">
        <p className="eyebrow">Export pipeline</p>
        <h1 className="section-title mt-3 text-4xl font-semibold text-white sm:text-5xl">Export history and reliability</h1>
        <p className="mt-4 max-w-3xl text-base subtle-copy sm:text-lg">
          Track every export attempt from the editorial workflow. Each record shows whether the draft was successfully
          exported, which operator triggered it, and what happened if the export failed.
        </p>

        <div className="mt-6 grid gap-4 md:grid-cols-3">
          <article className="rounded-[1.4rem] border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.55)] p-4">
            <ArrowDownToLine className="h-5 w-5 text-[color:var(--accent-blue)]" aria-hidden="true" />
            <p className="mt-4 text-sm font-semibold text-white">Total exports</p>
            <p className="mt-2 text-3xl font-semibold text-white">{rows.length}</p>
          </article>
          <article className="rounded-[1.4rem] border border-[rgba(52,211,153,0.22)] bg-[rgba(52,211,153,0.1)] p-4">
            <CheckCircle2 className="h-5 w-5 text-[color:var(--accent-green)]" aria-hidden="true" />
            <p className="mt-4 text-sm font-semibold text-white">Successful</p>
            <p className="mt-2 text-3xl font-semibold text-white">{successful}</p>
          </article>
          <article className="rounded-[1.4rem] border border-[rgba(251,113,133,0.22)] bg-[rgba(251,113,133,0.1)] p-4">
            <XCircle className="h-5 w-5 text-[color:var(--accent-rose)]" aria-hidden="true" />
            <p className="mt-4 text-sm font-semibold text-white">Failed</p>
            <p className="mt-2 text-3xl font-semibold text-white">{failed}</p>
          </article>
        </div>
      </section>

      <SectionCard
        eyebrow="Export log"
        title="All export attempts"
        description="Sorted by most recent first. Click a draft title to view its full detail and content."
      >
        {rows.length > 0 ? (
          <ExportTable rows={rows} />
        ) : (
          <EmptyState
            compact
            title="No export attempts recorded"
            description="Export records will appear here once drafts are exported from the editorial workflow."
          />
        )}
      </SectionCard>
    </div>
  );
}
