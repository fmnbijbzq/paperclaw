import type { LucideIcon } from "lucide-react";

import { formatCompactNumber } from "@/lib/format";

interface MetricCardProps {
  label: string;
  value: number;
  detail: string;
  icon: LucideIcon;
}

export function MetricCard({ label, value, detail, icon: Icon }: MetricCardProps) {
  return (
    <article className="panel-card rounded-[1.6rem] p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium subtle-copy">{label}</p>
          <p className="metric-value mt-3 text-white">{formatCompactNumber(value)}</p>
        </div>
        <span className="rounded-2xl border border-[rgba(96,165,250,0.22)] bg-[rgba(96,165,250,0.12)] p-3 text-[color:var(--accent-blue)]">
          <Icon className="h-5 w-5" aria-hidden="true" />
        </span>
      </div>
      <p className="mt-4 text-sm subtle-copy">{detail}</p>
    </article>
  );
}
