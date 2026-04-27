import Link from "next/link";
import type { Route } from "next";
import { SearchX } from "lucide-react";

interface EmptyStateProps {
  title: string;
  description: string;
  actionHref?: Route;
  actionLabel?: string;
}

export function EmptyState({ title, description, actionHref, actionLabel }: EmptyStateProps) {
  return (
    <div className="panel-card rounded-[1.75rem] px-6 py-10 text-center">
      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl border border-[rgba(245,158,11,0.22)] bg-[rgba(245,158,11,0.12)] text-[color:var(--accent-amber)]">
        <SearchX className="h-6 w-6" aria-hidden="true" />
      </div>
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
