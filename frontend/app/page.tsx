import Link from "next/link";
import { ArrowRight, BellRing, BookOpen, Database, FileStack, Sparkles } from "lucide-react";

import { EditorialPreviewCard } from "@/components/editorial-preview-card";
import { EmptyState } from "@/components/empty-state";
import { MetricCard } from "@/components/metric-card";
import { PaperList } from "@/components/paper-list";
import { PipelineTimeline } from "@/components/pipeline-timeline";
import { SectionCard } from "@/components/section-card";
import { SourceHealthCard } from "@/components/source-health-card";
import { getDashboardSnapshot } from "@/lib/queries";

export default async function OverviewPage() {
  const snapshot = await getDashboardSnapshot();
  const recentDrafts = snapshot.editorialDrafts.slice(0, 4);

  return (
    <div className="space-y-6 lg:space-y-8">
      <section className="panel-card rounded-[2rem] px-6 py-7 sm:px-8 sm:py-9">
        <div className="grid gap-8 xl:grid-cols-[minmax(0,1.5fr)_minmax(20rem,0.9fr)] xl:items-end">
          <div>
            <p className="eyebrow">研究收录可视化</p>
            <h1 className="section-title mt-3 max-w-4xl text-4xl font-semibold text-white sm:text-5xl">
              面向 Paperclaw 抓取、洞察、通知和编辑流程的协同控制台。
            </h1>
            <p className="mt-4 max-w-3xl text-base subtle-copy sm:text-lg">
              这个前端将现有 Python 流水线变成可探索的运营界面：已发现哪些论文、哪些已有洞察覆盖、
              哪些飞书投递需要重试，以及哪些内容产物已准备审核。
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link href="/papers" className="action-button action-button-primary">
                浏览论文
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
              <Link href="/pipeline" className="action-button action-button-secondary">
                查看流水线
              </Link>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
            <div className="rounded-[1.5rem] border border-[rgba(96,165,250,0.22)] bg-[rgba(96,165,250,0.1)] p-5">
              <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[color:var(--accent-blue)]">
                系统态势
              </p>
              <p className="mt-3 text-2xl font-semibold text-white">运营状态稳定</p>
              <p className="mt-2 text-sm subtle-copy">
                来源收录已运行，高价值论文已附加洞察，下游内容产物也已生成。
              </p>
            </div>
            <div className="rounded-[1.5rem] border border-[rgba(245,158,11,0.22)] bg-[rgba(245,158,11,0.1)] p-5">
              <p className="text-sm font-semibold uppercase tracking-[0.18em] text-[color:var(--accent-amber)]">
                队列监控
              </p>
              <p className="mt-3 text-2xl font-semibold text-white">
                {snapshot.metrics.pendingNotifications.value} 个重试待处理
              </p>
              <p className="mt-2 text-sm subtle-copy">
                失败的通知尝试会持续可见，发送可靠性排查无需直接触碰数据库。
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
        eyebrow="来源健康度"
        title="发现渠道覆盖情况"
        description="后端的来源适配器保持解耦，因此界面会独立汇总稳定性和收录量。"
      >
        {snapshot.sourceHealth.length > 0 ? (
          <div className="grid gap-4 lg:grid-cols-3">
            {snapshot.sourceHealth.map((item) => (
              <SourceHealthCard key={item.source} item={item} />
            ))}
          </div>
        ) : (
          <EmptyState
            compact
            title="暂无来源遥测数据"
            description="仓库返回爬虫状态数据后，来源健康度会显示在这里。"
          />
        )}
      </SectionCard>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(22rem,0.8fr)]">
        <SectionCard
          eyebrow="流水线"
          title="当前工作流状态"
          description="前端直接映射到已实现的 Paperclaw 阶段，并标出未来由界面驱动的工作流可扩展位置。"
        >
          {snapshot.pipelineStages.length > 0 ? (
            <PipelineTimeline stages={snapshot.pipelineStages} />
          ) : (
            <EmptyState
              compact
              title="未返回流水线阶段"
              description="后端集成接入后，这个视图即可展示实时阶段数据。"
            />
          )}
        </SectionCard>

        <SectionCard
          eyebrow="编辑产出"
          title="最新平台草稿"
          description="后端流程中已经存在 Markdown 草稿产物；控制台将其呈现为可审核的内容库存。"
        >
          {recentDrafts.length > 0 ? (
            <div className="space-y-4">
              {recentDrafts.map((draft) => (
                <EditorialPreviewCard key={draft.draftId} draft={draft} />
              ))}
            </div>
          ) : (
            <EmptyState
              compact
              title="暂无编辑草稿"
              description="编辑阶段生成输出后，Markdown 产物会显示在这里。"
            />
          )}
        </SectionCard>
      </div>

      <SectionCard
        eyebrow="近期发现"
        title="工作集中的最新论文"
        description="高密度论文行会持续展示来源、投递和洞察状态，便于以研究为先的浏览。"
        actions={
          <Link href="/papers" className="action-button action-button-secondary">
            <BookOpen className="h-4 w-4" aria-hidden="true" />
            查看全部论文
          </Link>
        }
      >
        {snapshot.recentPapers.length > 0 ? (
          <PaperList records={snapshot.recentPapers} />
        ) : (
          <EmptyState
            compact
            title="工作集中暂无近期论文"
            description="发现数据可用后，最新记录会连同洞察和通知上下文显示在这里。"
          />
        )}
      </SectionCard>
    </div>
  );
}
