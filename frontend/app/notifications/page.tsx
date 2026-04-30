import { BellRing, ShieldAlert, ShieldCheck } from "lucide-react";

import { EmptyState } from "@/components/empty-state";
import { NotificationTable } from "@/components/notification-table";
import { SectionCard } from "@/components/section-card";
import { getNotificationFeed, listPaperRecords } from "@/lib/queries";

export default async function NotificationsPage() {
  const [feed, records] = await Promise.all([getNotificationFeed(), listPaperRecords()]);
  const paperMap = new Map(records.map((record) => [record.paper.paperId, record]));

  const rows = feed.map((notification) => {
    const record = paperMap.get(notification.paperId);

    return {
      notification,
      paperTitle: record?.paper.title ?? `论文 ${notification.paperId}`,
      source: record?.paper.source ?? "arxiv",
    };
  });

  const successful = feed.filter((item) => item.success).length;
  const failed = feed.length - successful;

  return (
    <div className="space-y-6 lg:space-y-8">
      <section className="panel-card rounded-[2rem] px-6 py-7 sm:px-8 sm:py-9">
        <p className="eyebrow">投递健康度</p>
        <h1 className="section-title mt-3 text-4xl font-semibold text-white sm:text-5xl">飞书通知可靠性与重试可见性</h1>
        <p className="mt-4 max-w-3xl text-base subtle-copy sm:text-lg">
          Paperclaw 有意将通知状态与存储成功状态解耦。本页面让操作者清楚看到这种分离。
        </p>
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          <article className="rounded-[1.4rem] border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.55)] p-4">
            <BellRing className="h-5 w-5 text-[color:var(--accent-blue)]" aria-hidden="true" />
            <p className="mt-4 text-sm font-semibold text-white">尝试总数</p>
            <p className="mt-2 text-3xl font-semibold text-white">{feed.length}</p>
          </article>
          <article className="rounded-[1.4rem] border border-[rgba(52,211,153,0.22)] bg-[rgba(52,211,153,0.1)] p-4">
            <ShieldCheck className="h-5 w-5 text-[color:var(--accent-green)]" aria-hidden="true" />
            <p className="mt-4 text-sm font-semibold text-white">成功投递</p>
            <p className="mt-2 text-3xl font-semibold text-white">{successful}</p>
          </article>
          <article className="rounded-[1.4rem] border border-[rgba(251,113,133,0.22)] bg-[rgba(251,113,133,0.1)] p-4">
            <ShieldAlert className="h-5 w-5 text-[color:var(--accent-rose)]" aria-hidden="true" />
            <p className="mt-4 text-sm font-semibold text-white">需要重试的失败</p>
            <p className="mt-2 text-3xl font-semibold text-white">{failed}</p>
          </article>
        </div>
      </section>

      <SectionCard
        eyebrow="通知日志"
        title="近期投递尝试"
        description="每一行展示单篇论文的状态、目标、时间和重试上下文，后续可由实时后端 API 供数。"
      >
        {rows.length > 0 ? (
          <NotificationTable rows={rows} />
        ) : (
          <EmptyState
            compact
            title="暂无投递尝试记录"
            description="仓库返回发布或发送活动后，通知尝试会显示在这里。"
          />
        )}
      </SectionCard>
    </div>
  );
}
