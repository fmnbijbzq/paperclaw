import Link from "next/link";
import type { Route } from "next";
import { SearchX } from "lucide-react";

import { cx } from "@/lib/utils";

interface EmptyStateProps {
  eyebrow?: string;
  title: string;
  description: string;
  actionHref?: Route;
  actionLabel?: string;
  compact?: boolean;
}

export function EmptyState({ eyebrow, title, description, actionHref, actionLabel, compact = false }: EmptyStateProps) {
  return (
    <div
      className={cx(
        compact
          ? "rounded-[1.5rem] border border-dashed border-[rgba(96,165,250,0.24)] bg-[rgba(7,17,31,0.36)] px-6 py-8 text-center"
          : "panel-card rounded-[1.75rem] px-6 py-10 text-center",
      )}
    >
      <div
        className={cx(
          "mx-auto flex items-center justify-center rounded-2xl border border-[rgba(245,158,11,0.22)] bg-[rgba(245,158,11,0.12)] text-[color:var(--accent-amber)]",
          compact ? "h-12 w-12" : "h-14 w-14",
        )}
      >
        <SearchX className={cx(compact ? "h-5 w-5" : "h-6 w-6")} aria-hidden="true" />
      </div>
      {eyebrow ? <p className="eyebrow mt-5">{eyebrow}</p> : null}
      <h2 className="section-title mt-5 text-2xl font-semibold text-white">{title}</h2>
      <p className="mx-auto mt-3 max-w-xl text-sm subtle-copy">{description}</p>
      {actionHref && actionLabel ? (
        <Link href={actionHref} className="action-button action-button-secondary mt-6">
          {actionLabel}
        </Link>
      ) : null}
    </div>
  );
}
