import { ArrowDownToLine, CheckCircle2, XCircle } from "lucide-react";

import { EmptyState } from "@/components/empty-state";
import { ExportTable } from "@/components/export-table";
import { SectionCard } from "@/components/section-card";
import { getExportRecords } from "@/lib/queries";

export default async function ExportsPage() {
  const rows = await getExportRecords();

  const successful = rows.filter((row) => row.record.success).length;
  const failed = rows.length - successful;

  return (
    <div className="space-y-6 lg:space-y-8">
      <section className="panel-card rounded-[2rem] px-6 py-7 sm:px-8 sm:py-9">
        <p className="eyebrow">导出流水线</p>
        <h1 className="section-title mt-3 text-4xl font-semibold text-white sm:text-5xl">导出历史与可靠性</h1>
        <p className="mt-4 max-w-3xl text-base subtle-copy sm:text-lg">
          追踪编辑工作流中的每一次导出尝试。每条记录都会显示草稿是否成功导出、由哪位操作者触发，
          以及导出失败时发生了什么。
        </p>

        <div className="mt-6 grid gap-4 md:grid-cols-3">
          <article className="rounded-[1.4rem] border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.55)] p-4">
            <ArrowDownToLine className="h-5 w-5 text-[color:var(--accent-blue)]" aria-hidden="true" />
            <p className="mt-4 text-sm font-semibold text-white">导出总数</p>
            <p className="mt-2 text-3xl font-semibold text-white">{rows.length}</p>
          </article>
          <article className="rounded-[1.4rem] border border-[rgba(52,211,153,0.22)] bg-[rgba(52,211,153,0.1)] p-4">
            <CheckCircle2 className="h-5 w-5 text-[color:var(--accent-green)]" aria-hidden="true" />
            <p className="mt-4 text-sm font-semibold text-white">成功</p>
            <p className="mt-2 text-3xl font-semibold text-white">{successful}</p>
          </article>
          <article className="rounded-[1.4rem] border border-[rgba(251,113,133,0.22)] bg-[rgba(251,113,133,0.1)] p-4">
            <XCircle className="h-5 w-5 text-[color:var(--accent-rose)]" aria-hidden="true" />
            <p className="mt-4 text-sm font-semibold text-white">失败</p>
            <p className="mt-2 text-3xl font-semibold text-white">{failed}</p>
          </article>
        </div>
      </section>

      <SectionCard
        eyebrow="导出日志"
        title="全部导出尝试"
        description="按最新时间优先排序。点击草稿标题可查看完整详情和内容。"
      >
        {rows.length > 0 ? (
          <ExportTable rows={rows} />
        ) : (
          <EmptyState
            compact
            title="暂无导出尝试记录"
            description="从编辑工作流导出草稿后，导出记录会显示在这里。"
          />
        )}
      </SectionCard>
    </div>
  );
}
