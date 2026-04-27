import { AlertTriangle, CheckCircle2, Clock3, Info, XCircle } from "lucide-react";

import { cx } from "@/lib/utils";

type StatusTone = "success" | "warning" | "danger" | "info" | "neutral";

const toneStyles: Record<StatusTone, string> = {
  success: "border-[rgba(52,211,153,0.22)] bg-[rgba(52,211,153,0.12)] text-[color:var(--accent-green)]",
  warning: "border-[rgba(245,158,11,0.22)] bg-[rgba(245,158,11,0.12)] text-[color:var(--accent-amber)]",
  danger: "border-[rgba(251,113,133,0.22)] bg-[rgba(251,113,133,0.12)] text-[color:var(--accent-rose)]",
  info: "border-[rgba(96,165,250,0.22)] bg-[rgba(96,165,250,0.12)] text-[color:var(--accent-blue)]",
  neutral: "border-[color:var(--border-subtle)] bg-[rgba(15,23,42,0.65)] text-white",
};

const icons = {
  success: CheckCircle2,
  warning: AlertTriangle,
  danger: XCircle,
  info: Info,
  neutral: Clock3,
} satisfies Record<StatusTone, React.ComponentType<{ className?: string }>>;

interface StatusBadgeProps {
  label: string;
  tone?: StatusTone;
  className?: string;
}

export function StatusBadge({ label, tone = "neutral", className }: StatusBadgeProps) {
  const Icon = icons[tone];

  return (
    <span
      className={cx(
        "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold tracking-[0.02em]",
        toneStyles[tone],
        className,
      )}
    >
      <Icon className="h-3.5 w-3.5" aria-hidden="true" />
      {label}
    </span>
  );
}
