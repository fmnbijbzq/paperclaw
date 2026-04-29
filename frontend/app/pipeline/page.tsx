import { ArrowRight, CheckCircle2, Clock3, Sparkles } from "lucide-react";

import { EmptyState } from "@/components/empty-state";
import { PipelineTimeline } from "@/components/pipeline-timeline";
import { CrawlRunList, SummarizationRunList, EditorialRunList } from "@/components/run-history";
import { SectionCard } from "@/components/section-card";
import { StatusBadge } from "@/components/status-badge";
import { getDashboardSnapshot, getPipelineRunsSnapshot } from "@/lib/queries";

const extensionPoints = [
  {
    title: "Approval workflow",
    detail: "Introduce review states and ownership for editorial artifacts before export.",
    tone: "info" as const,
  },
  {
    title: "Destination audit trail",
    detail: "Track multi-channel publish/export outcomes beyond Feishu bot delivery status.",
    tone: "warning" as const,
  },
];

export default async function PipelinePage() {
  const [snapshot, runs] = await Promise.all([
    getDashboardSnapshot(),
    getPipelineRunsSnapshot(),
  ]);

  return (
    <div className="space-y-6 lg:space-y-8">
      <section className="panel-card rounded-[2rem] px-6 py-7 sm:px-8 sm:py-9">
        <p className="eyebrow">Pipeline map</p>
        <h1 className="section-title mt-3 text-4xl font-semibold text-white sm:text-5xl">From fetch to export, with implementation boundaries visible</h1>
        <p className="mt-4 max-w-3xl text-base subtle-copy sm:text-lg">
          The frontend is deliberately aligned to the current Python scripts so future API integration can replace demo data without changing the interaction model.
        </p>
      </section>

      <SectionCard
        eyebrow="Current stages"
        title="What Paperclaw already does"
        description="Each stage references concrete backend files and keeps the UI grounded in the existing codebase rather than an imagined product roadmap."
      >
        {snapshot.pipelineStages.length > 0 ? (
          <PipelineTimeline stages={snapshot.pipelineStages} />
        ) : (
          <EmptyState
            compact
            title="No pipeline stages returned"
            description="This page is ready for live stage data once the backend-facing data source is introduced."
          />
        )}
      </SectionCard>

      <SectionCard
        eyebrow="Run history"
        title="Crawl runs"
        description="Recent crawl execution records showing source, timing, success/failure, and fetch counts."
      >
        <CrawlRunList runs={runs.crawlRuns} />
      </SectionCard>

      <div className="grid gap-6 xl:grid-cols-2">
        <SectionCard
          eyebrow="Run history"
          title="Summarization runs"
          description="Tracks how many papers were processed and how many insights were generated per run."
        >
          <SummarizationRunList runs={runs.summarizationRuns} />
        </SectionCard>

        <SectionCard
          eyebrow="Run history"
          title="Editorial runs"
          description="Records editorial draft generation runs with paper and draft counts."
        >
          <EditorialRunList runs={runs.editorialRuns} />
        </SectionCard>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(24rem,0.9fr)]">
        <SectionCard
          eyebrow="Operational interpretation"
          title="How this console frames the workflow"
          description="These panels explain how the frontend turns script outputs into operator-friendly status surfaces."
        >
          <div className="grid gap-4 md:grid-cols-3">
            <article className="rounded-[1.4rem] border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.55)] p-4">
              <CheckCircle2 className="h-5 w-5 text-[color:var(--accent-green)]" aria-hidden="true" />
              <h2 className="mt-4 text-lg font-semibold text-white">Stored first</h2>
              <p className="mt-2 text-sm subtle-copy">
                Persistence and enrichment are visible even when downstream delivery fails.
              </p>
            </article>
            <article className="rounded-[1.4rem] border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.55)] p-4">
              <Clock3 className="h-5 w-5 text-[color:var(--accent-amber)]" aria-hidden="true" />
              <h2 className="mt-4 text-lg font-semibold text-white">Retries stay inspectable</h2>
              <p className="mt-2 text-sm subtle-copy">
                Failed notification attempts remain first-class records instead of disappearing into logs.
              </p>
            </article>
            <article className="rounded-[1.4rem] border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.55)] p-4">
              <Sparkles className="h-5 w-5 text-[color:var(--accent-blue)]" aria-hidden="true" />
              <h2 className="mt-4 text-lg font-semibold text-white">Editorial outputs are inventory</h2>
              <p className="mt-2 text-sm subtle-copy">
                Generated markdown is surfaced as reviewable product inventory, not just files on disk.
              </p>
            </article>
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="Extension points"
          title="What the next frontend iteration could own"
          description="Areas where UI-driven workflow would add value once backend APIs and state transitions are exposed."
        >
          <div className="space-y-4">
            {extensionPoints.map((item) => (
              <article
                key={item.title}
                className="rounded-[1.4rem] border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.55)] p-4"
              >
                <div className="flex items-center gap-3">
                  <StatusBadge label={item.title} tone={item.tone} />
                  <ArrowRight className="h-4 w-4 text-[color:var(--text-dim)]" aria-hidden="true" />
                </div>
                <p className="mt-3 text-sm subtle-copy">{item.detail}</p>
              </article>
            ))}
          </div>
        </SectionCard>
      </div>
    </div>
  );
}
