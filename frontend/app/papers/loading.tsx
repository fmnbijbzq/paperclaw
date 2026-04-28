import { LoadingPanel } from "@/components/loading-panel";

export default function PapersLoading() {
  return (
    <div className="space-y-6 lg:space-y-8">
      <LoadingPanel
        eyebrow="Paper inventory"
        title="Loading the working paper set"
        description="Fetching repository-backed paper records and insight summaries for the research browsing view."
        cardCount={2}
      />
      <LoadingPanel
        eyebrow="Paper records"
        title="Preparing dense rows for browsing"
        description="Joining delivery state and editorial artifact counts before the table of papers renders."
        cardCount={3}
      />
    </div>
  );
}
