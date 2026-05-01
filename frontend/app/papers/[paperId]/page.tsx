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
    title: record ? `${record.paper.title} · Paperclaw 控制台` : "未找到论文 · Paperclaw 控制台",
  };
}

export default async function PaperDetailPage({ params }: PaperDetailPageProps) {
  const { paperId } = await params;
  const parsedPaperId = Number(paperId);

  if (!Number.isInteger(parsedPaperId)) {
    return (
      <EmptyState
        eyebrow="论文详情"
        title="论文 ID 无效"
        description="请求的路由片段不是有效的数字论文 ID，因此协同应用无法解析详情记录。"
        actionHref="/papers"
        actionLabel="返回论文列表"
      />
    );
  }

  const record = await getPaperDetail(parsedPaperId);

  if (!record) {
    return (
      <EmptyState
        eyebrow="论文详情"
        title="未找到论文"
        description="演示数据集中不包含请求的论文 ID。在实时集成中，该视图会直接映射到后端论文查询。"
        actionHref="/papers"
        actionLabel="返回论文列表"
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
        <InsightPanel
          title="短摘要"
          body={record.insight?.summaryShort}
          isPlaceholder={record.insight?.isPlaceholder}
        />
        <InsightPanel
          title="长摘要"
          body={record.insight?.summaryLong}
          isPlaceholder={record.insight?.isPlaceholder}
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <InsightPanel
          title="创新点"
          items={record.insight?.noveltyPoints}
          isPlaceholder={record.insight?.isPlaceholder}
        />
        <InsightPanel
          title="局限性"
          items={record.insight?.limitations}
          isPlaceholder={record.insight?.isPlaceholder}
        />
        <InsightPanel
          title="应用场景"
          items={record.insight?.applications}
          isPlaceholder={record.insight?.isPlaceholder}
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(22rem,0.9fr)]">
        <SectionCard
          eyebrow="通知历史"
          title="投递尝试"
          description="匹配后端通知日志模型，并让重试原因保持可见。"
        >
          {notificationRows.length > 0 ? (
            <NotificationTable rows={notificationRows} />
          ) : (
            <EmptyState
              compact
              title="暂无通知尝试记录"
              description="这篇论文尚未尝试飞书投递，因此没有可查看的重试历史。"
            />
          )}
        </SectionCard>

        <SectionCard
          eyebrow="编辑产出"
          title="平台产物"
          description="预览与这篇论文关联的已生成 Markdown 内容产物。"
        >
          <div className="space-y-4">
            {record.editorialDrafts.length > 0 ? (
              record.editorialDrafts.map((draft) => <EditorialPreviewCard key={draft.draftId} draft={draft} />)
            ) : (
              <EmptyState
                compact
                title="暂无关联编辑产物"
                description="草稿生成尚未为这篇论文产出哔哩哔哩、小红书或抖音内容。"
              />
            )}
          </div>
        </SectionCard>
      </div>
    </div>
  );
}
