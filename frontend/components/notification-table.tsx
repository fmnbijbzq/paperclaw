import Link from "next/link";

import { formatDateTime, formatSource } from "@/lib/format";
import type { NotificationFeedRow } from "@/lib/types";
import { StatusBadge } from "@/components/status-badge";

interface NotificationTableProps {
  rows: NotificationFeedRow[];
}

export function NotificationTable({ rows }: NotificationTableProps) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full border-separate border-spacing-y-3">
        <caption className="sr-only">近期论文的通知发送尝试</caption>
        <thead>
          <tr className="text-left text-xs font-semibold uppercase tracking-[0.18em] text-[color:var(--text-dim)]">
            <th scope="col" className="px-4 py-2">
              论文
            </th>
            <th scope="col" className="px-4 py-2">
              来源
            </th>
            <th scope="col" className="px-4 py-2">
              目标
            </th>
            <th scope="col" className="px-4 py-2">
              状态
            </th>
            <th scope="col" className="px-4 py-2">
              尝试时间
            </th>
            <th scope="col" className="px-4 py-2">
              错误
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map(({ notification, paperTitle, source }) => (
            <tr key={notification.notificationId} className="panel-card rounded-[1.2rem] align-top">
              <td className="rounded-l-[1.2rem] px-4 py-4">
                <Link href={`/papers/${notification.paperId}`} className="font-semibold text-white">
                  {paperTitle}
                </Link>
              </td>
              <td className="px-4 py-4 text-sm subtle-copy">{formatSource(source)}</td>
              <td className="px-4 py-4 text-sm text-white">{notification.destination}</td>
              <td className="px-4 py-4">
                <StatusBadge label={notification.success ? "已送达" : "失败"} tone={notification.success ? "success" : "danger"} />
              </td>
              <td className="px-4 py-4 text-sm subtle-copy">{formatDateTime(notification.sentAt)}</td>
              <td className="rounded-r-[1.2rem] px-4 py-4 text-sm subtle-copy">
                {notification.errorMessage ?? "暂无错误记录"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
