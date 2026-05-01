import { ArrowRight, CheckCircle2, Clock3, Sparkles } from "lucide-react";

import { EmptyState } from "@/components/empty-state";
import { PipelineTaskControl } from "@/components/pipeline-task-control";
import { PipelineTimeline } from "@/components/pipeline-timeline";
import { CrawlRunList, SummarizationRunList, EditorialRunList } from "@/components/run-history";
import { SectionCard } from "@/components/section-card";
import { StatusBadge } from "@/components/status-badge";
import { getDashboardSnapshot, getPipelineRunsSnapshot, getPipelineTasks } from "@/lib/queries";
import { resolveRuntimeConfig } from "@/lib/runtime-config";

const extensionPoints = [
  {
    title: "审批工作流",
    detail: "在导出前为编辑产物引入审核状态和负责人归属。",
    tone: "info" as const,
  },
  {
    title: "目标端审计轨迹",
    detail: "除飞书机器人投递状态外，继续追踪多渠道发布和导出结果。",
    tone: "warning" as const,
  },
];

export default async function PipelinePage() {
  const runtimeConfig = resolveRuntimeConfig();
  const [snapshot, runs, tasks] = await Promise.all([
    getDashboardSnapshot(),
    getPipelineRunsSnapshot(),
    getPipelineTasks(),
  ]);

  return (
    <div className="space-y-6 lg:space-y-8">
      <section className="panel-card rounded-[2rem] px-6 py-7 sm:px-8 sm:py-9">
        <p className="eyebrow">流水线图谱</p>
        <h1 className="section-title mt-3 text-4xl font-semibold text-white sm:text-5xl">从抓取到导出，清晰呈现实现边界</h1>
        <p className="mt-4 max-w-3xl text-base subtle-copy sm:text-lg">
          前端刻意对齐当前 Python 脚本，因此未来 API 集成可以替换演示数据，而无需改变交互模型。
        </p>
      </section>

      <SectionCard
        eyebrow="当前阶段"
        title="Paperclaw 已经完成的能力"
        description="每个阶段都引用具体后端文件，让界面扎根于现有代码库，而不是假想的产品路线图。"
      >
        {snapshot.pipelineStages.length > 0 ? (
          <PipelineTimeline stages={snapshot.pipelineStages} />
        ) : (
          <EmptyState
            compact
            title="未返回流水线阶段"
            description="面向后端的数据源接入后，本页面即可展示实时阶段数据。"
          />
        )}
      </SectionCard>

      <SectionCard
        eyebrow="主动执行"
        title="流水线任务"
        description="手动启动抓取、洞察、草稿生成和可选飞书通知；导出仍保持审核后人工触发。"
      >
        <PipelineTaskControl
          apiBaseUrl={runtimeConfig.apiBaseUrl}
          apiKey={runtimeConfig.apiKey}
          dataSource={runtimeConfig.dataSource}
          initialTasks={tasks}
        />
      </SectionCard>

      <SectionCard
        eyebrow="运行历史"
        title="爬取运行"
        description="近期爬取执行记录，展示来源、时间、成功/失败状态和抓取数量。"
      >
        <CrawlRunList runs={runs.crawlRuns} />
      </SectionCard>

      <div className="grid gap-6 xl:grid-cols-2">
        <SectionCard
          eyebrow="运行历史"
          title="摘要运行"
          description="追踪每次运行处理了多少论文，并生成了多少洞察。"
        >
          <SummarizationRunList runs={runs.summarizationRuns} />
        </SectionCard>

        <SectionCard
          eyebrow="运行历史"
          title="编辑运行"
          description="记录编辑草稿生成运行，并展示论文和草稿数量。"
        >
          <EditorialRunList runs={runs.editorialRuns} />
        </SectionCard>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(24rem,0.9fr)]">
        <SectionCard
          eyebrow="运营解读"
          title="控制台如何组织工作流"
          description="这些面板说明前端如何将脚本输出转化为对操作者友好的状态界面。"
        >
          <div className="grid gap-4 md:grid-cols-3">
            <article className="rounded-[1.4rem] border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.55)] p-4">
              <CheckCircle2 className="h-5 w-5 text-[color:var(--accent-green)]" aria-hidden="true" />
              <h2 className="mt-4 text-lg font-semibold text-white">先入库存储</h2>
              <p className="mt-2 text-sm subtle-copy">
                即使下游投递失败，持久化和富化结果仍然可见。
              </p>
            </article>
            <article className="rounded-[1.4rem] border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.55)] p-4">
              <Clock3 className="h-5 w-5 text-[color:var(--accent-amber)]" aria-hidden="true" />
              <h2 className="mt-4 text-lg font-semibold text-white">重试保持可检查</h2>
              <p className="mt-2 text-sm subtle-copy">
                失败的通知尝试会保留为一等记录，而不是消失在日志里。
              </p>
            </article>
            <article className="rounded-[1.4rem] border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.55)] p-4">
              <Sparkles className="h-5 w-5 text-[color:var(--accent-blue)]" aria-hidden="true" />
              <h2 className="mt-4 text-lg font-semibold text-white">编辑产出即库存</h2>
              <p className="mt-2 text-sm subtle-copy">
                已生成的 Markdown 会作为可审核的产品库存展示，而不只是磁盘上的文件。
              </p>
            </article>
          </div>
        </SectionCard>

        <SectionCard
          eyebrow="扩展点"
          title="下一轮前端迭代可承接的部分"
          description="当后端 API 和状态转换开放后，这些区域可以通过界面驱动的工作流继续增值。"
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
