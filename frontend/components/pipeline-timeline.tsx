import { ArrowRight, Code2, Sparkles } from "lucide-react";

import { StatusBadge } from "@/components/status-badge";
import type { PipelineStageItem } from "@/lib/types";

const toneMap = {
  live: "success",
  partial: "warning",
  planned: "info",
} as const;

interface PipelineTimelineProps {
  stages: PipelineStageItem[];
}

export function PipelineTimeline({ stages }: PipelineTimelineProps) {
  return (
    <ol className="space-y-4">
      {stages.map((stage, index) => (
        <li key={stage.stageId} className="relative rounded-[1.5rem] border border-[color:var(--border-subtle)] bg-[rgba(15,23,42,0.52)] p-4">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
            <div className="flex items-start gap-4">
              <div className="flex flex-col items-center">
                <span className="flex h-10 w-10 items-center justify-center rounded-2xl border border-[rgba(96,165,250,0.22)] bg-[rgba(96,165,250,0.12)] text-sm font-semibold text-[color:var(--accent-blue)]">
                  {index + 1}
                </span>
                {index < stages.length - 1 ? (
                  <span className="mt-2 flex h-full min-h-10 items-center justify-center text-[color:var(--text-dim)]">
                    <ArrowRight className="h-4 w-4 rotate-90 xl:rotate-0" aria-hidden="true" />
                  </span>
                ) : null}
              </div>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-3">
                  <h3 className="text-lg font-semibold text-white">{stage.name}</h3>
                  <StatusBadge label={stage.status} tone={toneMap[stage.status]} />
                </div>
                <p className="mt-2 text-sm subtle-copy">{stage.summary}</p>
              </div>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 xl:w-[26rem]">
              <div className="rounded-2xl border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.55)] p-3">
                <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-[color:var(--accent-blue)]">
                  <Code2 className="h-4 w-4" aria-hidden="true" />
                  Implemented in
                </p>
                <ul className="mt-3 space-y-2 text-sm text-white">
                  {stage.implementedIn.map((path) => (
                    <li key={path} className="truncate font-mono text-xs text-slate-200">
                      {path}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="rounded-2xl border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.55)] p-3">
                <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-[color:var(--accent-amber)]">
                  <Sparkles className="h-4 w-4" aria-hidden="true" />
                  Evidence
                </p>
                <p className="mt-3 text-sm subtle-copy">{stage.evidence}</p>
              </div>
            </div>
          </div>
        </li>
      ))}
    </ol>
  );
}
