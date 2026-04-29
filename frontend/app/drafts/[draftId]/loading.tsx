import { LoadingPanel } from "@/components/loading-panel";

export default function DraftDetailLoading() {
  return (
    <div className="space-y-6 lg:space-y-8">
      <LoadingPanel
        eyebrow="Draft detail"
        title="Loading editorial draft context"
        description="Resolving the requested draft, its paper source, and export history for the detail view."
        cardCount={2}
      />
      <LoadingPanel
        eyebrow="Draft content"
        title="Preparing markdown preview and audit trail"
        description="Loading the generated markdown content and activity timeline."
        cardCount={2}
      />
      <LoadingPanel
        eyebrow="Export history"
        title="Collecting export attempts"
        description="Fetching export records associated with this editorial draft."
        cardCount={2}
      />
    </div>
  );
}
