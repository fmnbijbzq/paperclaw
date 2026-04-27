import { Search } from "lucide-react";

import { PaperList } from "@/components/paper-list";
import { SectionCard } from "@/components/section-card";
import { searchPapers } from "@/lib/queries";

export default function PapersPage() {
  const records = searchPapers();

  return (
    <div className="space-y-6 lg:space-y-8">
      <section className="panel-card rounded-[2rem] px-6 py-7 sm:px-8 sm:py-9">
        <p className="eyebrow">Paper inventory</p>
        <h1 className="section-title mt-3 text-4xl font-semibold text-white sm:text-5xl">Research intake across crawlers</h1>
        <p className="mt-4 max-w-3xl text-base subtle-copy sm:text-lg">
          This view is shaped around the backend paper + insight + notification model, so you can inspect discovery, enrichment,
          and downstream readiness in one place.
        </p>
        <div className="mt-6 flex max-w-xl items-center gap-3 rounded-[1.5rem] border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.6)] px-4 py-3">
          <Search className="h-4 w-4 text-[color:var(--accent-blue)]" aria-hidden="true" />
          <div>
            <p className="text-sm font-semibold text-white">Search-ready layout</p>
            <p className="text-sm subtle-copy">
              The current demo dataset is rendered in full. Query helpers already support title, author, venue, category, and summary matching.
            </p>
          </div>
        </div>
      </section>

      <SectionCard
        eyebrow="Paper records"
        title={`${records.length} papers in the current working set`}
        description="Rows emphasize source, summary confidence, draft count, and notification state for high-density browsing."
      >
        <PaperList records={records} />
      </SectionCard>
    </div>
  );
}
