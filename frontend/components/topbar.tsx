import Link from "next/link";
import { Activity, BellDot, Database, Workflow } from "lucide-react";

import { StatusBadge } from "@/components/status-badge";
import { formatDateTime } from "@/lib/format";
import { getDashboardSnapshot } from "@/lib/queries";

export async function Topbar() {
  const snapshot = await getDashboardSnapshot();
  const latestRun = [...snapshot.sourceHealth].sort(
    (left, right) => new Date(right.lastRunAt).getTime() - new Date(left.lastRunAt).getTime(),
  )[0];

  return (
    <header className="sticky top-0 z-30 border-b border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.84)] backdrop-blur-xl">
      <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-4 px-4 py-4 sm:px-6 lg:flex-row lg:items-center lg:justify-between lg:px-8">
        <div>
          <p className="eyebrow">协同工作区</p>
          <div className="mt-2 flex flex-wrap items-center gap-3">
            <h2 className="section-title text-xl font-semibold text-white">Paperclaw 研究运营</h2>
            <StatusBadge label="演示数据集" tone="info" />
          </div>
          <p className="mt-2 text-sm subtle-copy">
            最新来源活动记录于 {latestRun ? formatDateTime(latestRun.lastRunAt) : "暂无"}。
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="panel-card rounded-full px-4 py-2">
            <div className="flex items-center gap-2 text-sm text-white">
              <Database className="h-4 w-4 text-[color:var(--accent-blue)]" aria-hidden="true" />
              <span>{snapshot.metrics.totalPapers.value} 篇论文</span>
            </div>
          </div>
          <div className="panel-card rounded-full px-4 py-2">
            <div className="flex items-center gap-2 text-sm text-white">
              <BellDot className="h-4 w-4 text-[color:var(--accent-amber)]" aria-hidden="true" />
              <span>{snapshot.metrics.pendingNotifications.value} 个待发送</span>
            </div>
          </div>
          <div className="panel-card rounded-full px-4 py-2">
            <div className="flex items-center gap-2 text-sm text-white">
              <Activity className="h-4 w-4 text-[color:var(--accent-green)]" aria-hidden="true" />
              <span>{snapshot.metrics.papersWithInsights.value} 篇已生成洞察</span>
            </div>
          </div>
          <Link href="/pipeline" className="action-button action-button-primary">
            <Workflow className="h-4 w-4" aria-hidden="true" />
            打开流水线
          </Link>
        </div>
      </div>
    </header>
  );
}
