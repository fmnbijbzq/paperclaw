import { BellRing, ShieldAlert, ShieldCheck } from "lucide-react";

import { NotificationTable } from "@/components/notification-table";
import { SectionCard } from "@/components/section-card";
import { getNotificationFeed, listPaperRecords } from "@/lib/queries";

export default function NotificationsPage() {
  const feed = getNotificationFeed();
  const records = listPaperRecords();
  const paperMap = new Map(records.map((record) => [record.paper.paperId, record]));

  const rows = feed.map((notification) => {
    const record = paperMap.get(notification.paperId);

    return {
      notification,
      paperTitle: record?.paper.title ?? `Paper ${notification.paperId}`,
      source: record?.paper.source ?? "arxiv",
    };
  });

  const successful = feed.filter((item) => item.success).length;
  const failed = feed.length - successful;

  return (
    <div className="space-y-6 lg:space-y-8">
      <section className="panel-card rounded-[2rem] px-6 py-7 sm:px-8 sm:py-9">
        <p className="eyebrow">Delivery health</p>
        <h1 className="section-title mt-3 text-4xl font-semibold text-white sm:text-5xl">Feishu notification reliability and retry visibility</h1>
        <p className="mt-4 max-w-3xl text-base subtle-copy sm:text-lg">
          Notification state is intentionally decoupled from storage success in Paperclaw. This page makes that separation legible for operators.
        </p>
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          <article className="rounded-[1.4rem] border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.55)] p-4">
            <BellRing className="h-5 w-5 text-[color:var(--accent-blue)]" aria-hidden="true" />
            <p className="mt-4 text-sm font-semibold text-white">Total attempts</p>
            <p className="mt-2 text-3xl font-semibold text-white">{feed.length}</p>
          </article>
          <article className="rounded-[1.4rem] border border-[rgba(52,211,153,0.22)] bg-[rgba(52,211,153,0.1)] p-4">
            <ShieldCheck className="h-5 w-5 text-[color:var(--accent-green)]" aria-hidden="true" />
            <p className="mt-4 text-sm font-semibold text-white">Successful deliveries</p>
            <p className="mt-2 text-3xl font-semibold text-white">{successful}</p>
          </article>
          <article className="rounded-[1.4rem] border border-[rgba(251,113,133,0.22)] bg-[rgba(251,113,133,0.1)] p-4">
            <ShieldAlert className="h-5 w-5 text-[color:var(--accent-rose)]" aria-hidden="true" />
            <p className="mt-4 text-sm font-semibold text-white">Failures requiring retry</p>
            <p className="mt-2 text-3xl font-semibold text-white">{failed}</p>
          </article>
        </div>
      </section>

      <SectionCard
        eyebrow="Notification log"
        title="Recent delivery attempts"
        description="Rows show per-paper status, destination, timing, and retry context in a form that could later be fed from live backend APIs."
      >
        <NotificationTable rows={rows} />
      </SectionCard>
    </div>
  );
}
