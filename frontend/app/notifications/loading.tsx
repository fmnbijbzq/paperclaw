import { LoadingPanel } from "@/components/loading-panel";

export default function NotificationsLoading() {
  return (
    <div className="space-y-6 lg:space-y-8">
      <LoadingPanel
        eyebrow="Delivery health"
        title="Loading notification reliability metrics"
        description="Preparing successful sends, retry-needed failures, and the latest delivery timestamps."
        cardCount={3}
      />
      <LoadingPanel
        eyebrow="Notification log"
        title="Collecting recent delivery attempts"
        description="Joining per-paper metadata and notification outcomes before the table of attempts renders."
        cardCount={3}
      />
    </div>
  );
}
