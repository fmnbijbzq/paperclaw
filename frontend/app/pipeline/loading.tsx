import { LoadingPanel } from "@/components/loading-panel";

export default function PipelineLoading() {
  return (
    <div className="space-y-6 lg:space-y-8">
      <LoadingPanel
        eyebrow="Pipeline map"
        title="Loading stage boundaries"
        description="Preparing the current fetch, normalize, store, insight, editorial, and export stages for the operations view."
        cardCount={2}
      />
      <LoadingPanel
        eyebrow="Current stages"
        title="Collecting evidence and implementation paths"
        description="Hydrating the code references and operational evidence associated with each backend pipeline stage."
        cardCount={3}
      />
    </div>
  );
}
