import { LoadingPanel } from "@/components/loading-panel";

export default function PaperDetailLoading() {
  return (
    <div className="space-y-6 lg:space-y-8">
      <LoadingPanel
        eyebrow="Paper detail"
        title="Loading paper context and insight state"
        description="Resolving the requested paper record, notification history, and editorial drafts for the detail view."
        cardCount={2}
      />
      <LoadingPanel
        eyebrow="Insight summaries"
        title="Preparing the attached analysis panels"
        description="Hydrating short summary, long summary, novelty points, limitations, and applications."
        cardCount={3}
      />
      <LoadingPanel
        eyebrow="Downstream activity"
        title="Collecting delivery and editorial history"
        description="Joining recent notification attempts with platform-specific content artifacts."
        cardCount={2}
      />
    </div>
  );
}
