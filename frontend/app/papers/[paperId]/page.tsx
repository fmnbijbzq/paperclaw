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
  const record = await getPaperDetail(Number(paperId));

  return {
    title: record ? `${record.paper.title} · Paperclaw Console` : "Paper not found · Paperclaw Console",
  };
}

export default async function PaperDetailPage({ params }: PaperDetailPageProps) {
  const { paperId } = await params;
  const parsedPaperId = Number(paperId);

  if (!Number.isInteger(parsedPaperId)) {
    return (
      <EmptyState
        eyebrow="Paper detail"
        title="Paper id is invalid"
        description="The requested route segment is not a valid numeric paper id, so the companion app cannot resolve a detail record."
        actionHref="/papers"
        actionLabel="Back to papers"
      />
    );
  }

  const record = await getPaperDetail(parsedPaperId);

  if (!record) {
    return (
      <EmptyState
        eyebrow="Paper detail"
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
            <EmptyState
              compact
              title="No notification attempts recorded"
              description="Feishu delivery has not been attempted for this paper yet, so there is no retry history to inspect."
            />
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
              <EmptyState
                compact
                title="No editorial artifacts attached"
                description="Draft generation has not produced Bilibili, Xiaohongshu, or Douyin artifacts for this paper yet."
              />
            )}
          </div>
        </SectionCard>
      </div>
    </div>
  );
}
