import Link from "next/link";
import { ArrowRight, BellRing, BookOpen, Database, FileStack, Sparkles } from "lucide-react";

import { EditorialPreviewCard } from "@/components/editorial-preview-card";
import { MetricCard } from "@/components/metric-card";
import { PaperList } from "@/components/paper-list";
import { PipelineTimeline } from "@/components/pipeline-timeline";
import { SectionCard } from "@/components/section-card";
import { SourceHealthCard } from "@/components/source-health-card";
import { getDashboardSnapshot } from "@/lib/queries";

export default function OverviewPage() {
  const snapshot = getDashboardSnapshot();

  return (
    <div className="space-y-6 lg:space-y-8">
      <section className="panel-card rounded-[2rem] px-6 py-7 sm:px-8 sm:py-9">
        <div className="grid gap-8 xl:grid-cols-[minmax(0,1.5fr)_minmax(20rem,0.9fr)] xl:items-end">
          <div>
            <p className="eyebrow">Research intake visibility</p>
            <h1 className="section-title mt-3 max-w-4xl text-4xl font-semibold text-white sm:text-5xl">
              A companion console for Paperclaw’s fetch, insight, notification, and editorial workflow.
            </h1>
            <p className="mt-4 max-w-3xl text-base subtle-copy sm:text-lg">
              This frontend turns the existing Python pipeline into an explorable operations surface: what was discovered,
              what has insight coverage, which Feishu deliveries need retries, and which content artifacts are ready for review.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link href="/papers" className="action-button action-button-primary">
                Browse papers
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
              <Link href="/pipeline" className="action-button action-button-secondary">
                Inspect pipeline
              </Link>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
            <div className="rounded-[1.5rem] border border-[rgba(96,165,250,0.22)] bg-[rgba(96,165,250,0.1)] p-5">
              <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[color:var(--accent-blue)]">
                System posture
              </p>
              <p className="mt-3 text-2xl font-semibold text-white">Operationally stable</p>
              <p className="mt-2 text-sm subtle-copy">
                Source ingest is live, insights are attached for high-value papers, and downstream content artifacts are present.
              </p>
            </div>
            <div className="rounded-[1.5rem] border border-[rgba(245,158,11,0.22)] bg-[rgba(245,158,11,0.1)] p-5">
              <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[color:var(--accent-amber)]">
                Queue watch
              </p>
              <p className="mt-3 text-2xl font-semibold text-white">
                {snapshot.metrics.pendingNotifications.value} retries pending
              </p>
              <p className="mt-2 text-sm subtle-copy">
                Failed notification attempts stay visible so send reliability can be debugged without touching the database.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard {...snapshot.metrics.totalPapers} icon={Database} />
        <MetricCard {...snapshot.metrics.papersWithInsights} icon={Sparkles} />
        <MetricCard {...snapshot.metrics.pendingNotifications} icon={BellRing} />
        <MetricCard {...snapshot.metrics.editorialDrafts} icon={FileStack} />
      </section>

      <SectionCard
        eyebrow="Source health"
        title="Coverage across discovery channels"
        description="Source adapters remain decoupled in the backend, so the UI summarizes stability and intake volume independently."
      >
        <div className="grid gap-4 lg:grid-cols-3">
          {snapshot.sourceHealth.map((item) => (
            <SourceHealthCard key={item.source} item={item} />
          ))}
        </div>
      </SectionCard>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(22rem,0.8fr)]">
        <SectionCard
          eyebrow="Pipeline"
          title="Current workflow state"
          description="Maps the frontend directly to the implemented Paperclaw stages and highlights where future UI-driven workflow could expand."
        >
          <PipelineTimeline stages={snapshot.pipelineStages} />
        </SectionCard>

        <SectionCard
          eyebrow="Editorial outputs"
          title="Most recent platform drafts"
          description="Draft markdown artifacts already exist in the backend flow; the console exposes them as reviewable content inventory."
        >
          <div className="space-y-4">
            {snapshot.editorialDrafts.slice(0, 4).map((draft) => (
              <EditorialPreviewCard key={draft.draftId} draft={draft} />
            ))}
          </div>
        </SectionCard>
      </div>

      <SectionCard
        eyebrow="Recent discoveries"
        title="Newest papers in the working set"
        description="Dense paper rows keep source, delivery, and insight state visible for research-first browsing."
        actions={
          <Link href="/papers" className="action-button action-button-secondary">
            <BookOpen className="h-4 w-4" aria-hidden="true" />
            View all papers
          </Link>
        }
      >
        <PaperList records={snapshot.recentPapers} />
      </SectionCard>
    </div>
  );
}
