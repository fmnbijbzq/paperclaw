import { Suspense } from "react";

import { EmptyState } from "@/components/empty-state";
import { PaperSearchForm } from "@/components/paper-search-form";
import { PaperList } from "@/components/paper-list";
import { SectionCard } from "@/components/section-card";
import { searchPapers } from "@/lib/queries";
import type { PaperSource } from "@/lib/types";

interface PapersPageProps {
  searchParams: Promise<{
    q?: string;
    source?: string;
    page?: string;
  }>;
}

const validSources: PaperSource[] = ["arxiv", "openreview", "cvf"];

export default async function PapersPage({ searchParams }: PapersPageProps) {
  const { q: rawQuery, source: rawSource, page: rawPage } = await searchParams;

  const query = rawQuery ?? "";
  const source: PaperSource | "all" = rawSource && validSources.includes(rawSource as PaperSource) ? (rawSource as PaperSource) : "all";
  const page = rawPage ? Math.max(1, Number.parseInt(rawPage, 10) || 1) : 1;

  const result = await searchPapers({
    q: query || undefined,
    source: source !== "all" ? source : undefined,
    page,
    pageSize: 20,
  });

  const { records, total, totalPages } = result;

  return (
    <div className="space-y-6 lg:space-y-8">
      <section className="panel-card rounded-[2rem] px-6 py-7 sm:px-8 sm:py-9">
        <p className="eyebrow">Paper inventory</p>
        <h1 className="section-title mt-3 text-4xl font-semibold text-white sm:text-5xl">Research intake across crawlers</h1>
        <p className="mt-4 max-w-3xl text-base subtle-copy sm:text-lg">
          Search and browse papers from arXiv, OpenReview, and CVF. Use the search bar and source filter to find specific papers.
        </p>

        <div className="mt-6">
          <Suspense>
            <PaperSearchForm initialQuery={query} initialSource={source} />
          </Suspense>
        </div>
      </section>

      <SectionCard
        eyebrow="Paper records"
        title={query ? `${total} results for "${query}"` : `${total} papers in the current working set`}
        description={
          query
            ? `Showing page ${page} of ${totalPages}. Results match title, author, venue, category, and summary content.`
            : "Rows emphasize source, summary confidence, draft count, and notification state for high-density browsing."
        }
      >
        {records.length > 0 ? (
          <>
            <PaperList records={records} />
            {totalPages > 1 && (
              <div className="mt-6 flex items-center justify-center gap-3">
                {page > 1 ? (
                  <a
                    href={`/papers?${new URLSearchParams({ ...(query && { q: query }), ...(source !== "all" && { source }), page: String(page - 1) }).toString()}`}
                    className="action-button action-button-secondary"
                  >
                    Previous
                  </a>
                ) : (
                  <span className="action-button action-button-secondary pointer-events-none opacity-40">Previous</span>
                )}
                <span className="text-sm subtle-copy">
                  Page {page} of {totalPages}
                </span>
                {page < totalPages ? (
                  <a
                    href={`/papers?${new URLSearchParams({ ...(query && { q: query }), ...(source !== "all" && { source }), page: String(page + 1) }).toString()}`}
                    className="action-button action-button-secondary"
                  >
                    Next
                  </a>
                ) : (
                  <span className="action-button action-button-secondary pointer-events-none opacity-40">Next</span>
                )}
              </div>
            )}
          </>
        ) : (
          <EmptyState
            compact
            title={query ? "No papers match your search" : "No papers are available yet"}
            description={
              query
                ? `No results found for "${query}". Try a different search term or adjust the source filter.`
                : "When the repository returns paper records, they will render here with insight, delivery, and editorial context."
            }
          />
        )}
      </SectionCard>
    </div>
  );
}
