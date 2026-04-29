import { Activity, AlertTriangle, CheckCircle2, Clock3, FileText, Layers, RefreshCw, XCircle } from "lucide-react";

import { StatusBadge } from "@/components/status-badge";
import { formatDateTime, formatDuration, formatSource, formatRunStatus } from "@/lib/format";
import type { CrawlRunItem, EditorialRunItem, RunStatus, SummarizationRunItem } from "@/lib/types";

const statusTone: Record<RunStatus, "success" | "danger" | "warning"> = {
  success: "success",
  failed: "danger",
  running: "warning",
};

const statusIcon: Record<RunStatus, typeof CheckCircle2> = {
  success: CheckCircle2,
  failed: XCircle,
  running: RefreshCw,
};

function SuccessRate({ total, successes }: { total: number; successes: number }) {
  const rate = total > 0 ? successes / total : 0;
  const pct = Math.round(rate * 100);
  return (
    <span className={pct >= 80 ? "text-[color:var(--accent-green)]" : pct >= 50 ? "text-[color:var(--accent-amber)]" : "text-[color:var(--accent-rose)]"}>
      {pct}% ({successes}/{total})
    </span>
  );
}

function RunRow({
  status,
  startedAt,
  durationSeconds,
  errorMessage,
  children,
}: {
  status: RunStatus;
  startedAt: string;
  durationSeconds: number | null;
  errorMessage: string | null;
  children: React.ReactNode;
}) {
  const Icon = statusIcon[status];

  return (
    <li className="rounded-[1.2rem] border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.55)] p-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-start gap-3">
          <span className="mt-0.5 text-[color:var(--text-dim)]">
            <Icon className={`h-4 w-4 ${status === "running" ? "animate-spin" : ""}`} aria-hidden="true" />
          </span>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge label={formatRunStatus(status)} tone={statusTone[status]} />
              <span className="text-xs text-[color:var(--text-dim)]">{formatDateTime(startedAt)}</span>
              {durationSeconds !== null ? (
                <span className="text-xs text-[color:var(--text-dim)]">
                  <Clock3 className="mr-1 inline-block h-3 w-3" aria-hidden="true" />
                  {formatDuration(durationSeconds)}
                </span>
              ) : null}
            </div>
            <div className="mt-2 flex flex-wrap gap-3 text-sm">
              {children}
            </div>
            {errorMessage ? (
              <p className="mt-2 flex items-start gap-2 text-sm text-[color:var(--accent-rose)]">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                <span>{errorMessage}</span>
              </p>
            ) : null}
          </div>
        </div>
      </div>
    </li>
  );
}

function StatPill({ label, value }: { label: string; value: string | number }) {
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-[color:var(--border-subtle)] bg-[rgba(15,23,42,0.6)] px-3 py-1 text-xs">
      <span className="subtle-copy">{label}</span>
      <span className="font-semibold text-white">{value}</span>
    </span>
  );
}

interface CrawlRunListProps {
  runs: CrawlRunItem[];
}

export function CrawlRunList({ runs }: CrawlRunListProps) {
  if (runs.length === 0) {
    return (
      <div className="rounded-[1.2rem] border border-dashed border-[rgba(96,165,250,0.24)] bg-[rgba(7,17,31,0.36)] px-6 py-8 text-center">
        <Activity className="mx-auto h-5 w-5 text-[color:var(--text-dim)]" aria-hidden="true" />
        <p className="mt-3 text-sm subtle-copy">No crawl runs recorded yet.</p>
      </div>
    );
  }

  const successCount = runs.filter((r) => r.status === "success").length;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4 text-sm">
        <span className="subtle-copy">Success rate:</span>
        <SuccessRate total={runs.length} successes={successCount} />
      </div>
      <ol className="space-y-3">
        {runs.map((run) => (
          <RunRow
            key={run.runId}
            status={run.status}
            startedAt={run.startedAt}
            durationSeconds={run.durationSeconds}
            errorMessage={run.errorMessage}
          >
            <StatPill label="Source" value={formatSource(run.source)} />
            <StatPill label="Fetched" value={run.fetchedCount} />
            <StatPill label="New" value={run.newCount} />
          </RunRow>
        ))}
      </ol>
    </div>
  );
}

interface SummarizationRunListProps {
  runs: SummarizationRunItem[];
}

export function SummarizationRunList({ runs }: SummarizationRunListProps) {
  if (runs.length === 0) {
    return (
      <div className="rounded-[1.2rem] border border-dashed border-[rgba(96,165,250,0.24)] bg-[rgba(7,17,31,0.36)] px-6 py-8 text-center">
        <Layers className="mx-auto h-5 w-5 text-[color:var(--text-dim)]" aria-hidden="true" />
        <p className="mt-3 text-sm subtle-copy">No summarization runs recorded yet.</p>
      </div>
    );
  }

  const successCount = runs.filter((r) => r.status === "success").length;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4 text-sm">
        <span className="subtle-copy">Success rate:</span>
        <SuccessRate total={runs.length} successes={successCount} />
      </div>
      <ol className="space-y-3">
        {runs.map((run) => (
          <RunRow
            key={run.runId}
            status={run.status}
            startedAt={run.startedAt}
            durationSeconds={run.durationSeconds}
            errorMessage={run.errorMessage}
          >
            <StatPill label="Papers" value={run.papersProcessed} />
            <StatPill label="Insights" value={run.insightsGenerated} />
          </RunRow>
        ))}
      </ol>
    </div>
  );
}

interface EditorialRunListProps {
  runs: EditorialRunItem[];
}

export function EditorialRunList({ runs }: EditorialRunListProps) {
  if (runs.length === 0) {
    return (
      <div className="rounded-[1.2rem] border border-dashed border-[rgba(96,165,250,0.24)] bg-[rgba(7,17,31,0.36)] px-6 py-8 text-center">
        <FileText className="mx-auto h-5 w-5 text-[color:var(--text-dim)]" aria-hidden="true" />
        <p className="mt-3 text-sm subtle-copy">No editorial runs recorded yet.</p>
      </div>
    );
  }

  const successCount = runs.filter((r) => r.status === "success").length;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-4 text-sm">
        <span className="subtle-copy">Success rate:</span>
        <SuccessRate total={runs.length} successes={successCount} />
      </div>
      <ol className="space-y-3">
        {runs.map((run) => (
          <RunRow
            key={run.runId}
            status={run.status}
            startedAt={run.startedAt}
            durationSeconds={run.durationSeconds}
            errorMessage={run.errorMessage}
          >
            <StatPill label="Papers" value={run.papersProcessed} />
            <StatPill label="Drafts" value={run.draftsGenerated} />
          </RunRow>
        ))}
      </ol>
    </div>
  );
}
