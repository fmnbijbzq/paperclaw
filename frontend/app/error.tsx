"use client";

import { ErrorPanel } from "@/components/error-panel";

interface AppErrorProps {
  error: Error & {
    digest?: string;
  };
  reset: () => void;
}

export default function AppError({ error, reset }: AppErrorProps) {
  return (
    <ErrorPanel
      title="当前页面加载失败"
      description="控制台在解析该视图时遇到异常，后端数据和演示数据集没有被修改。"
      detail={error.digest ? `错误引用：${error.digest}` : "请重试当前页面，或返回仪表盘概览。"}
      onRetry={reset}
      actionHref="/"
      actionLabel="返回仪表盘"
    />
  );
}
