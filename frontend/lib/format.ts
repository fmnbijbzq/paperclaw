import type { DraftStatus, EditorialPlatform, PaperSource } from "./types";

const compactNumberFormatter = new Intl.NumberFormat("en", {
  notation: "compact",
  maximumFractionDigits: 1,
});

const shortDateFormatter = new Intl.DateTimeFormat("en", {
  month: "short",
  day: "numeric",
});

const fullDateFormatter = new Intl.DateTimeFormat("en", {
  month: "short",
  day: "numeric",
  year: "numeric",
});

const dateTimeFormatter = new Intl.DateTimeFormat("en", {
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

export function formatCompactNumber(value: number): string {
  return compactNumberFormatter.format(value);
}

export function formatDate(value: string): string {
  return shortDateFormatter.format(new Date(value));
}

export function formatFullDate(value: string): string {
  return fullDateFormatter.format(new Date(value));
}

export function formatDateTime(value: string): string {
  return `${dateTimeFormatter.format(new Date(value))} UTC`;
}

export function formatSource(source: PaperSource): string {
  const labels: Record<PaperSource, string> = {
    arxiv: "arXiv",
    openreview: "OpenReview",
    cvf: "CVF",
  };

  return labels[source];
}

export function formatPlatform(platform: EditorialPlatform): string {
  const labels: Record<EditorialPlatform, string> = {
    bilibili: "Bilibili",
    xiaohongshu: "Xiaohongshu",
    douyin: "Douyin",
  };

  return labels[platform];
}

export function formatDraftStatus(status: DraftStatus): string {
  const labels: Record<DraftStatus, string> = {
    generated: "Generated",
    in_review: "In review",
    approved: "Approved",
    rejected: "Rejected",
    exported: "Exported",
  };

  return labels[status];
}

export function formatPercent(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function formatDuration(seconds: number | null): string {
  if (seconds === null || seconds === undefined) {
    return "—";
  }
  if (seconds < 60) {
    return `${Math.round(seconds)}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.round(seconds % 60);
  return `${minutes}m ${remainingSeconds}s`;
}

export function formatRunStatus(status: string): string {
  const labels: Record<string, string> = {
    running: "Running",
    success: "Success",
    failed: "Failed",
  };
  return labels[status] ?? status;
}
