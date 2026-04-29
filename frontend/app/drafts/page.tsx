import { Suspense } from "react";

import { DraftFilterForm } from "@/components/draft-filter-form";
import { DraftTable } from "@/components/draft-table";
import { EmptyState } from "@/components/empty-state";
import { SectionCard } from "@/components/section-card";
import { StatusBadge } from "@/components/status-badge";
import { formatDraftStatus, formatPlatform } from "@/lib/format";
import { getDraftPlatformCounts, getDraftStatusCounts, getDraftList } from "@/lib/queries";
import type { DraftStatus, EditorialPlatform } from "@/lib/types";

interface DraftsPageProps {
  searchParams: Promise<{
    status?: string;
    platform?: string;
  }>;
}

export default async function DraftsPage({ searchParams }: DraftsPageProps) {
  const { status: rawStatus, platform: rawPlatform } = await searchParams;

  const validStatuses: DraftStatus[] = ["generated", "in_review", "approved", "rejected", "exported"];
  const validPlatforms: EditorialPlatform[] = ["bilibili", "xiaohongshu", "douyin"];

  const statusFilter: DraftStatus | "all" = rawStatus && validStatuses.includes(rawStatus as DraftStatus) ? (rawStatus as DraftStatus) : "all";
  const platformFilter: EditorialPlatform | "all" = rawPlatform && validPlatforms.includes(rawPlatform as EditorialPlatform) ? (rawPlatform as EditorialPlatform) : "all";

  const [drafts, statusCounts, platformCounts] = await Promise.all([
    getDraftList({ status: statusFilter, platform: platformFilter }),
    getDraftStatusCounts(),
    getDraftPlatformCounts(),
  ]);

  return (
    <div className="space-y-6 lg:space-y-8">
      <section className="panel-card rounded-[2rem] px-6 py-7 sm:px-8 sm:py-9">
        <p className="eyebrow">Editorial workflow</p>
        <h1 className="section-title mt-3 text-4xl font-semibold text-white sm:text-5xl">Draft management console</h1>
        <p className="mt-4 max-w-3xl text-base subtle-copy sm:text-lg">
          Review, approve, and export platform-specific editorial drafts for Bilibili, Xiaohongshu, and Douyin.
          Filter by status or platform to focus on your workflow stage.
        </p>

        <div className="mt-6 grid gap-4 sm:grid-cols-5">
          {validStatuses.map((status) => (
            <article
              key={status}
              className="rounded-[1.4rem] border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.55)] p-4"
            >
              <StatusBadge label={formatDraftStatus(status)} tone="neutral" />
              <p className="mt-3 text-2xl font-semibold text-white">{statusCounts[status]}</p>
            </article>
          ))}
        </div>

        <div className="mt-4 flex flex-wrap gap-3">
          {validPlatforms.map((platform) => (
            <div key={platform} className="inline-flex items-center gap-2 rounded-full border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.55)] px-3 py-1.5 text-sm">
              <span className="text-white font-medium">{formatPlatform(platform)}</span>
              <span className="subtle-copy">{platformCounts[platform]}</span>
            </div>
          ))}
        </div>
      </section>

      <SectionCard
        eyebrow="Draft list"
        title={`${drafts.length} draft${drafts.length === 1 ? "" : "s"} found`}
        description="Drafts are sorted by last update time. Click a title to view the full detail and take action."
        actions={
          <Suspense>
            <DraftFilterForm initialStatus={statusFilter} initialPlatform={platformFilter} />
          </Suspense>
        }
      >
        {drafts.length > 0 ? (
          <DraftTable drafts={drafts} />
        ) : (
          <EmptyState
            compact
            title="No drafts match filters"
            description="Try adjusting the status or platform filters, or remove them to see all drafts in the working set."
          />
        )}
      </SectionCard>
    </div>
  );
}
