import { EmptyState } from "@/components/empty-state";
import { SectionCard } from "@/components/section-card";

interface InsightPanelProps {
  title: string;
  body?: string | null;
  items?: string[];
  isPlaceholder?: boolean;
}

export function InsightPanel({ title, body, items, isPlaceholder }: InsightPanelProps) {
  const hasItems = Boolean(items && items.length > 0);
  const hasContent = Boolean(body) || hasItems;

  return (
    <SectionCard title={title} className="h-full">
      {hasContent && isPlaceholder ? (
        <p
          className="mb-3 inline-flex items-center gap-2 rounded-full border border-[color:var(--border-warning,#7a5a00)] bg-[rgba(122,90,0,0.18)] px-3 py-1 text-xs font-medium text-[color:var(--accent-amber)]"
          aria-label="未启用真实 AI 摘要，当前展示模板拼接结果"
        >
          ⚠ 模板生成内容
          <span className="font-normal text-[color:var(--text-dim)]">未启用 AI 摘要</span>
        </p>
      ) : null}
      {body ? <p className="text-sm leading-7 subtle-copy">{body}</p> : null}
      {hasItems ? (
        <ul className="space-y-3">
          {items?.map((item) => (
            <li
              key={item}
              className="rounded-2xl border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.5)] px-4 py-3 text-sm subtle-copy"
            >
              {item}
            </li>
          ))}
        </ul>
      ) : null}
      {!hasContent ? (
        <EmptyState
          compact
          title="洞察待生成"
          description="此部分尚未生成洞察内容。"
        />
      ) : null}
    </SectionCard>
  );
}
