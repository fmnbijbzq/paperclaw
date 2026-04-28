import { EmptyState } from "@/components/empty-state";
import { SectionCard } from "@/components/section-card";

interface InsightPanelProps {
  title: string;
  body?: string | null;
  items?: string[];
}

export function InsightPanel({ title, body, items }: InsightPanelProps) {
  const hasItems = Boolean(items && items.length > 0);

  return (
    <SectionCard title={title} className="h-full">
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
      {!body && !hasItems ? (
        <EmptyState
          compact
          title="Insight pending"
          description="Insight generation has not produced content for this section yet."
        />
      ) : null}
    </SectionCard>
  );
}
