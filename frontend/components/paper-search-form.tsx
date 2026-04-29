"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Search, X } from "lucide-react";
import { useCallback, useTransition } from "react";

import type { PaperSource } from "@/lib/types";

interface PaperSearchFormProps {
  initialQuery: string;
  initialSource: PaperSource | "all";
}

const sourceOptions: Array<{ value: PaperSource | "all"; label: string }> = [
  { value: "all", label: "All sources" },
  { value: "arxiv", label: "arXiv" },
  { value: "openreview", label: "OpenReview" },
  { value: "cvf", label: "CVF" },
];

export function PaperSearchForm({ initialQuery, initialSource }: PaperSearchFormProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isPending, startTransition] = useTransition();

  const updateSearchParams = useCallback(
    (updates: Record<string, string>) => {
      const params = new URLSearchParams(searchParams.toString());

      for (const [key, value] of Object.entries(updates)) {
        if (value) {
          params.set(key, value);
        } else {
          params.delete(key);
        }
      }

      params.delete("page");

      startTransition(() => {
        router.push(`/papers?${params.toString()}`);
      });
    },
    [router, searchParams, startTransition],
  );

  const handleQueryChange = useCallback(
    (value: string) => {
      updateSearchParams({ q: value });
    },
    [updateSearchParams],
  );

  const handleSourceChange = useCallback(
    (value: string) => {
      updateSearchParams({ source: value });
    },
    [updateSearchParams],
  );

  const handleClear = useCallback(() => {
    startTransition(() => {
      router.push("/papers");
    });
  }, [router, startTransition]);

  return (
    <div className="flex flex-col gap-4 sm:flex-row sm:items-end">
      <div className="flex-1">
        <label htmlFor="paper-search" className="sr-only">
          Search papers
        </label>
        <div className="relative">
          <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-[color:var(--accent-blue)]" aria-hidden="true" />
          <input
            id="paper-search"
            type="search"
            placeholder="Search by title, author, venue, or keyword..."
            defaultValue={initialQuery}
            onChange={(event) => handleQueryChange(event.target.value)}
            className="w-full rounded-[1.2rem] border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.6)] py-3 pl-11 pr-4 text-sm text-white placeholder-[color:var(--text-dim)] outline-none transition-colors focus:border-[color:var(--accent-blue)]"
          />
          {initialQuery && (
            <button
              type="button"
              onClick={handleClear}
              className="absolute right-3 top-1/2 -translate-y-1/2 rounded-lg p-1 text-[color:var(--text-dim)] transition-colors hover:text-white"
              aria-label="Clear search"
            >
              <X className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3">
        <label htmlFor="paper-source-filter" className="sr-only">
          Filter by source
        </label>
        <select
          id="paper-source-filter"
          defaultValue={initialSource}
          onChange={(event) => handleSourceChange(event.target.value)}
          className="rounded-[1.2rem] border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.6)] px-4 py-3 text-sm text-white outline-none transition-colors focus:border-[color:var(--accent-blue)]"
        >
          {sourceOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      {isPending && (
        <div className="inline-flex items-center gap-2 self-center rounded-full border border-[rgba(96,165,250,0.22)] bg-[rgba(96,165,250,0.12)] px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.16em] text-[color:var(--accent-blue)]">
          Searching
        </div>
      )}
    </div>
  );
}
