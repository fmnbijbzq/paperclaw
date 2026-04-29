import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft, FileText, User } from "lucide-react";

import { EmptyState } from "@/components/empty-state";
import { SectionCard } from "@/components/section-card";
import { StatusBadge } from "@/components/status-badge";
import { formatDateTime, formatDraftStatus, formatPlatform, formatSource } from "@/lib/format";
import { getDraftDetail } from "@/lib/queries";
import type { DraftStatus } from "@/lib/types";

interface DraftDetailPageProps {
  params: Promise<{
    draftId: string;
  }>;
}

function getDraftStatusTone(status: DraftStatus): "success" | "warning" | "danger" | "info" | "neutral" {
  const toneMap: Record<DraftStatus, "success" | "warning" | "danger" | "info" | "neutral"> = {
    generated: "neutral",
    in_review: "warning",
    approved: "success",
    rejected: "danger",
    exported: "info",
  };

  return toneMap[status];
}

export async function generateMetadata({ params }: DraftDetailPageProps): Promise<Metadata> {
  const { draftId } = await params;
  const record = await getDraftDetail(draftId);

  return {
    title: record ? `${record.draft.title} · Paperclaw Console` : "Draft not found · Paperclaw Console",
  };
}

export default async function DraftDetailPage({ params }: DraftDetailPageProps) {
  const { draftId } = await params;
  const record = await getDraftDetail(draftId);

  if (!record) {
    return (
      <EmptyState
        eyebrow="Draft detail"
        title="Draft not found"
        description="The requested draft does not exist in the current dataset. In a live integration this view would map directly to a backend draft lookup."
        actionHref="/drafts"
        actionLabel="Back to drafts"
      />
    );
  }

  const { draft, exportHistory, auditTrail } = record;

  return (
    <div className="space-y-6 lg:space-y-8">
      {/* Hero section */}
      <section className="panel-card rounded-[2rem] px-6 py-7 sm:px-8 sm:py-9">
        <div className="flex flex-wrap items-center gap-3">
          <Link
            href="/drafts"
            className="inline-flex items-center gap-2 rounded-full border border-[color:var(--border-subtle)] bg-[rgba(15,23,42,0.6)] px-3 py-1.5 text-xs font-semibold text-white transition-colors hover:border-[color:var(--accent-blue)]"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to drafts
          </Link>
          <StatusBadge label={formatPlatform(draft.platform)} tone="info" />
          <StatusBadge label={formatDraftStatus(draft.status)} tone={getDraftStatusTone(draft.status)} />
        </div>

        <h1 className="section-title mt-4 text-3xl font-semibold text-white sm:text-4xl">{draft.title}</h1>
        <p className="mt-3 text-base subtle-copy">{draft.hook}</p>

        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <article className="rounded-[1.2rem] border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.55)] p-4">
            <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--accent-blue)]">
              <FileText className="h-4 w-4" aria-hidden="true" />
              Paper
            </p>
            <p className="mt-3 text-sm text-white">{draft.paper.title}</p>
            <p className="mt-1 text-xs subtle-copy">{formatSource(draft.paper.source)} · {draft.paper.venue}</p>
          </article>
          <article className="rounded-[1.2rem] border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.55)] p-4">
            <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--accent-amber)]">
              <User className="h-4 w-4" aria-hidden="true" />
              Assignee
            </p>
            <p className="mt-3 text-sm text-white">{draft.assignee ?? "Unassigned"}</p>
          </article>
          <article className="rounded-[1.2rem] border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.55)] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--accent-blue)]">Last Updated</p>
            <p className="mt-3 text-sm text-white">{formatDateTime(draft.updatedAt)}</p>
          </article>
          <article className="rounded-[1.2rem] border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.55)] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--accent-blue)]">Output Path</p>
            <p className="mt-3 text-xs text-white break-all">{draft.outputPath}</p>
          </article>
        </div>

        {draft.reviewNote && (
          <div className="mt-4 rounded-[1.2rem] border border-[rgba(245,158,11,0.22)] bg-[rgba(245,158,11,0.08)] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--accent-amber)]">Review Note</p>
            <p className="mt-2 text-sm text-white">{draft.reviewNote}</p>
          </div>
        )}
      </section>

      {/* Content */}
      <SectionCard
        eyebrow="Draft content"
        title="Markdown preview"
        description="The generated markdown content for this editorial draft."
      >
        <div className="prose prose-invert max-w-none rounded-[1.2rem] border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.6)] p-5">
          <pre className="whitespace-pre-wrap text-sm text-white/90">{draft.markdownContent || "No content available."}</pre>
        </div>
      </SectionCard>
    </div>
  );
}
