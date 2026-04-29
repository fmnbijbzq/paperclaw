import { LoadingPanel } from "@/components/loading-panel";

export default function DraftsLoading() {
  return (
    <div className="space-y-6 lg:space-y-8">
      <LoadingPanel
        eyebrow="Editorial workflow"
        title="Loading draft management console"
        description="Fetching editorial drafts, status counts, and platform distribution for the browsing view."
        cardCount={3}
      />
      <LoadingPanel
        eyebrow="Draft list"
        title="Preparing draft rows"
        description="Sorting drafts by update time and applying status and platform filters."
        cardCount={3}
      />
    </div>
  );
}
