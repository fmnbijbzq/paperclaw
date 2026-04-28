import { LoadingPanel } from "@/components/loading-panel";

export default function AppLoading() {
  return (
    <div className="space-y-6 lg:space-y-8">
      <LoadingPanel
        eyebrow="Research intake visibility"
        title="Bootstrapping the Paperclaw console"
        description="Loading dashboard metrics, source health, and editorial inventory from the repository-backed companion data layer."
        cardCount={2}
      />
      <LoadingPanel
        eyebrow="Operational metrics"
        title="Hydrating high-density overview cards"
        description="Preparing insight coverage, pending retries, and draft inventory for the current working set."
        cardCount={4}
      />
      <LoadingPanel
        eyebrow="Recent discoveries"
        title="Ranking the latest paper records"
        description="Joining paper metadata with insights, notifications, and editorial drafts before the dashboard renders."
        cardCount={3}
      />
    </div>
  );
}
