import type { Metadata } from "next";

import { EditorialPreviewCard } from "@/components/editorial-preview-card";
import { EmptyState } from "@/components/empty-state";
import { InsightPanel } from "@/components/insight-panel";
import { NotificationTable } from "@/components/notification-table";
import { PaperDetailHero } from "@/components/paper-detail-hero";
import { SectionCard } from "@/components/section-card";
import { getPaperDetail } from "@/lib/queries";

interface PaperDetailPageProps {
  params: Promise<{
    paperId: string;
  }>;
}

export async function generateMetadata({ params }: PaperDetailPageProps): Promise<Metadata> {
  const { paperId } = await params;
  const record = getPaperDetail(Number(paperId));

  return {
    title: record ? `${record.paper.title} · Paperclaw Console` : "Paper not found · Paperclaw Console",
  };
}

export default async function PaperDetailPage({ params }: PaperDetailPageProps) {
  const { paperId } = await params;
  const record = getPaperDetail(Number(paperId));

  if (!record) {
    return (
      <EmptyState
        title="Paper not found"
        description="This demo dataset does not include the requested paper id. In a live integration this view would map directly to a backend paper lookup."
        actionHref="/papers"
        actionLabel="Back to papers"
      />
    );
  }

  const notificationRows = record.notifications.map((notification) => ({
    notification,
    paperTitle: record.paper.title,
    source: record.paper.source,
  }));

  return (
    <div className="space-y-6 lg:space-y-8">
      <PaperDetailHero record={record} />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(22rem,0.8fr)]">
        <InsightPanel title="Short summary" body={record.insight?.summaryShort} />
        <InsightPanel title="Long summary" body={record.insight?.summaryLong} />
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <InsightPanel title="Novelty points" items={record.insight?.noveltyPoints} />
        <InsightPanel title="Limitations" items={record.insight?.limitations} />
        <InsightPanel title="Applications" items={record.insight?.applications} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(22rem,0.9fr)]">
        <SectionCard
          eyebrow="Notification history"
          title="Delivery attempts"
          description="Matches the backend notification log model and makes retry causes visible."
        >
          {notificationRows.length > 0 ? (
            <NotificationTable rows={notificationRows} />
          ) : (
            <p className="text-sm subtle-copy">No notification attempts have been recorded for this paper yet.</p>
          )}
        </SectionCard>

        <SectionCard
          eyebrow="Editorial outputs"
          title="Platform artifacts"
          description="Preview of generated markdown content artifacts linked to this paper."
        >
          <div className="space-y-4">
            {record.editorialDrafts.length > 0 ? (
              record.editorialDrafts.map((draft) => <EditorialPreviewCard key={draft.draftId} draft={draft} />)
            ) : (
              <p className="text-sm subtle-copy">No draft artifacts are attached to this paper yet.</p>
            )}
          </div>
        </SectionCard>
      </div>
    </div>
  );
}
