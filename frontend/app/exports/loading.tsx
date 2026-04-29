import { LoadingPanel } from "@/components/loading-panel";

export default function ExportsLoading() {
  return (
    <div className="space-y-6 lg:space-y-8">
      <LoadingPanel
        eyebrow="Export pipeline"
        title="Loading export reliability metrics"
        description="Fetching total exports, successful attempts, and failure counts."
        cardCount={3}
      />
      <LoadingPanel
        eyebrow="Export log"
        title="Preparing export history rows"
        description="Joining export records with draft metadata for the browsing view."
        cardCount={3}
      />
    </div>
  );
}
