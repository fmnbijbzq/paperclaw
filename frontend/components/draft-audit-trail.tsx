import { formatDateTime } from "@/lib/format";
import type { DraftAuditEvent } from "@/lib/types";
import { StatusBadge } from "@/components/status-badge";

function getAuditTone(tone: DraftAuditEvent["tone"]): "success" | "warning" | "danger" | "info" | "neutral" {
  return tone;
}

interface DraftAuditTrailProps {
  events: DraftAuditEvent[];
}

export function DraftAuditTrail({ events }: DraftAuditTrailProps) {
  if (events.length === 0) {
    return <p className="text-sm subtle-copy">No audit events recorded.</p>;
  }

  return (
    <ol className="space-y-4">
      {events.map((event) => (
        <li key={event.eventId} className="flex items-start gap-4 rounded-[1.2rem] border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.55)] p-4">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge label={event.label} tone={getAuditTone(event.tone)} />
              <span className="text-xs subtle-copy">{formatDateTime(event.timestamp)}</span>
            </div>
            <p className="mt-2 text-sm text-white">{event.detail}</p>
          </div>
        </li>
      ))}
    </ol>
  );
}
