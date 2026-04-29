"use client";

import { useRouter, useSearchParams } from "next/navigation";
import type { Route } from "next";
import { useCallback, useTransition } from "react";

import type { DraftStatus, EditorialPlatform } from "@/lib/types";

interface DraftFilterFormProps {
  initialStatus: DraftStatus | "all";
  initialPlatform: EditorialPlatform | "all";
}

const statusOptions: Array<{ value: DraftStatus | "all"; label: string }> = [
  { value: "all", label: "All statuses" },
  { value: "generated", label: "Generated" },
  { value: "in_review", label: "In review" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
  { value: "exported", label: "Exported" },
];

const platformOptions: Array<{ value: EditorialPlatform | "all"; label: string }> = [
  { value: "all", label: "All platforms" },
  { value: "bilibili", label: "Bilibili" },
  { value: "xiaohongshu", label: "Xiaohongshu" },
  { value: "douyin", label: "Douyin" },
];

export function DraftFilterForm({ initialStatus, initialPlatform }: DraftFilterFormProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();

  const updateSearchParams = useCallback(
    (updates: Record<string, string>) => {
      const params = new URLSearchParams(searchParams.toString());

      for (const [key, value] of Object.entries(updates)) {
        if (value && value !== "all") {
          params.set(key, value);
        } else {
          params.delete(key);
        }
      }

      startTransition(() => {
        const queryString = params.toString();
        const href = `/drafts${queryString ? `?${queryString}` : ""}` as Route;
        router.push(href);
      });
    },
    [router, searchParams, startTransition],
  );

  return (
    <div className="flex flex-wrap items-center gap-3">
      <label htmlFor="draft-status-filter" className="sr-only">
        Filter by status
      </label>
      <select
        id="draft-status-filter"
        defaultValue={initialStatus}
        onChange={(event) => updateSearchParams({ status: event.target.value })}
        className="rounded-[1.2rem] border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.6)] px-4 py-3 text-sm text-white outline-none transition-colors focus:border-[color:var(--accent-blue)]"
      >
        {statusOptions.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>

      <label htmlFor="draft-platform-filter" className="sr-only">
        Filter by platform
      </label>
      <select
        id="draft-platform-filter"
        defaultValue={initialPlatform}
        onChange={(event) => updateSearchParams({ platform: event.target.value })}
        className="rounded-[1.2rem] border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.6)] px-4 py-3 text-sm text-white outline-none transition-colors focus:border-[color:var(--accent-blue)]"
      >
        {platformOptions.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>

      {isPending && (
        <div className="inline-flex items-center gap-2 rounded-full border border-[rgba(96,165,250,0.22)] bg-[rgba(96,165,250,0.12)] px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--accent-blue)]">
          Filtering
        </div>
      )}
    </div>
  );
}
