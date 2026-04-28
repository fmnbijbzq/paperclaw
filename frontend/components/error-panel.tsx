"use client";

import Link from "next/link";
import type { Route } from "next";
import { AlertTriangle, RefreshCcw } from "lucide-react";

interface ErrorPanelProps {
  title: string;
  description: string;
  detail?: string;
  actionHref?: Route;
  actionLabel?: string;
  onRetry?: () => void;
  retryLabel?: string;
}

export function ErrorPanel({
  title,
  description,
  detail,
  actionHref,
  actionLabel,
  onRetry,
  retryLabel = "Retry route",
}: ErrorPanelProps) {
  return (
    <section role="alert" className="panel-card rounded-[1.75rem] px-6 py-10 text-center sm:px-8">
      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl border border-[rgba(251,113,133,0.22)] bg-[rgba(251,113,133,0.12)] text-[color:var(--accent-rose)]">
        <AlertTriangle className="h-6 w-6" aria-hidden="true" />
      </div>
      <p className="eyebrow mt-5 text-[color:var(--accent-rose)]">Route recovery</p>
      <h1 className="section-title mt-3 text-3xl font-semibold text-white sm:text-4xl">{title}</h1>
      <p className="mx-auto mt-4 max-w-2xl text-sm subtle-copy sm:text-base">{description}</p>
      {detail ? (
        <div className="mx-auto mt-6 max-w-2xl rounded-[1.4rem] border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.58)] px-4 py-4 text-left">
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--accent-blue)]">Operational detail</p>
          <p className="mt-2 text-sm subtle-copy">{detail}</p>
        </div>
      ) : null}
      <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
        {onRetry ? (
          <button type="button" onClick={onRetry} className="action-button action-button-primary">
            <RefreshCcw className="h-4 w-4" aria-hidden="true" />
            {retryLabel}
          </button>
        ) : null}
        {actionHref && actionLabel ? (
          <Link href={actionHref} className={`action-button ${onRetry ? "action-button-secondary" : "action-button-primary"}`}>
            {actionLabel}
          </Link>
        ) : null}
      </div>
    </section>
  );
}
