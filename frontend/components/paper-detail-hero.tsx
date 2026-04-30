import { ArrowUpRight, BellRing, BrainCircuit, FileText, FileUp, Microscope } from "lucide-react";

import { formatFullDate, formatSource } from "@/lib/format";
import type { PaperRecord } from "@/lib/types";
import { StatusBadge } from "@/components/status-badge";

interface PaperDetailHeroProps {
  record: PaperRecord;
}

export function PaperDetailHero({ record }: PaperDetailHeroProps) {
  return (
    <section className="panel-card rounded-[2rem] p-6 sm:p-7">
      <div className="flex flex-col gap-6 xl:flex-row xl:items-start xl:justify-between">
        <div className="max-w-4xl">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge label={formatSource(record.paper.source)} tone="info" />
            <StatusBadge label={record.insight ? "洞察已就绪" : "洞察待生成"} tone={record.insight ? "success" : "neutral"} />
            <StatusBadge
              label={record.notifications[0]?.success ? "已投递到飞书" : record.notifications[0] ? "等待重试" : "尚未发送"}
              tone={record.notifications[0]?.success ? "success" : record.notifications[0] ? "danger" : "warning"}
            />
          </div>
          <h1 className="section-title mt-5 text-4xl font-semibold text-white sm:text-5xl">{record.paper.title}</h1>
          <p className="mt-4 max-w-3xl text-base subtle-copy">{record.paper.abstract}</p>
          <p className="mt-5 text-sm text-slate-200">{record.paper.authors.join(", ")}</p>
          <dl className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-2xl border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.55)] p-4">
              <dt className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--accent-blue)]">
                <Microscope className="h-4 w-4" aria-hidden="true" />
                会议/期刊
              </dt>
              <dd className="mt-2 text-sm text-white">{record.paper.venue}</dd>
            </div>
            <div className="rounded-2xl border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.55)] p-4">
              <dt className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--accent-blue)]">
                <FileText className="h-4 w-4" aria-hidden="true" />
                发表时间
              </dt>
              <dd className="mt-2 text-sm text-white">{formatFullDate(record.paper.publishedAt)}</dd>
            </div>
            <div className="rounded-2xl border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.55)] p-4">
              <dt className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--accent-blue)]">
                <BrainCircuit className="h-4 w-4" aria-hidden="true" />
                置信度
              </dt>
              <dd className="mt-2 text-sm text-white">
                {record.insight ? `${Math.round(record.insight.confidenceScore * 100)}% 置信度` : "未生成洞察"}
              </dd>
            </div>
            <div className="rounded-2xl border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.55)] p-4">
              <dt className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--accent-blue)]">
                <BellRing className="h-4 w-4" aria-hidden="true" />
                草稿
              </dt>
              <dd className="mt-2 text-sm text-white">{record.editorialDrafts.length} 个平台产物</dd>
            </div>
          </dl>
        </div>

        <div className="flex flex-col gap-3 xl:w-72">
          <a href={record.paper.paperUrl} target="_blank" rel="noreferrer" className="action-button action-button-primary">
            打开摘要页
            <ArrowUpRight className="h-4 w-4" aria-hidden="true" />
          </a>
          <a href={record.paper.pdfUrl} target="_blank" rel="noreferrer" className="action-button action-button-secondary">
            打开 PDF
            <FileUp className="h-4 w-4" aria-hidden="true" />
          </a>
          <div className="rounded-[1.5rem] border border-[rgba(245,158,11,0.18)] bg-[rgba(245,158,11,0.08)] p-4">
            <p className="text-sm font-semibold text-white">编辑就绪度</p>
            <p className="mt-2 text-sm subtle-copy">
              {record.editorialDrafts.length > 0
                ? "草稿产物已存在，剩余工作是审核、导出和可靠的下游通知。"
                : "此论文尚未生成草稿产物。"}
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
