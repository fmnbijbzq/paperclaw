import type { DraftStatus, EditorialPlatform, HealthStatus, PaperSource, StageStatus } from "./types";

const compactNumberFormatter = new Intl.NumberFormat("zh-CN", {
  notation: "compact",
  maximumFractionDigits: 1,
});

const shortDateFormatter = new Intl.DateTimeFormat("zh-CN", {
  month: "short",
  day: "numeric",
});

const fullDateFormatter = new Intl.DateTimeFormat("zh-CN", {
  month: "short",
  day: "numeric",
  year: "numeric",
});

const dateTimeFormatter = new Intl.DateTimeFormat("zh-CN", {
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  hour12: false,
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
    bilibili: "哔哩哔哩",
    xiaohongshu: "小红书",
    douyin: "抖音",
  };

  return labels[platform];
}

export function formatDraftStatus(status: DraftStatus): string {
  const labels: Record<DraftStatus, string> = {
    generated: "已生成",
    in_review: "审核中",
    approved: "已批准",
    rejected: "已拒绝",
    exported: "已导出",
  };

  return labels[status];
}

export function formatStageStatus(status: StageStatus): string {
  const labels: Record<StageStatus, string> = {
    live: "已上线",
    partial: "部分可用",
    planned: "计划中",
  };

  return labels[status];
}

export function formatHealthStatus(status: HealthStatus): string {
  const labels: Record<HealthStatus, string> = {
    healthy: "健康",
    degraded: "异常",
    attention: "需关注",
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
    return `${Math.round(seconds)} 秒`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.round(seconds % 60);
  return `${minutes} 分 ${remainingSeconds} 秒`;
}

export function formatRunStatus(status: string): string {
  const labels: Record<string, string> = {
    running: "运行中",
    success: "成功",
    failed: "失败",
  };
  return labels[status] ?? status;
}
