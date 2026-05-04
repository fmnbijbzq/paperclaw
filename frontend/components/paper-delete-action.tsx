"use client";

import { Loader2, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState, useTransition } from "react";

import type { ApiDataSource } from "@/lib/api-contracts";

interface PaperDeleteActionProps {
  paperId: number;
  paperTitle: string;
  draftCount: number;
  hasInsight: boolean;
  apiBaseUrl: string | null;
  apiKey: string | null;
  dataSource: ApiDataSource;
}

type Status = "idle" | "confirming" | "deleting" | "error";

const HTTP_ERROR_LABEL: Record<number, string> = {
  401: "未授权（API_KEY 不正确或未发送）",
  403: "未授权（API_KEY 不正确或未发送）",
  404: "未找到论文（可能已被删除）",
  503: "服务端未配置 API_KEY，无法删除",
};

function describeError(error: unknown): string {
  if (error instanceof Error) {
    // Errors raised below carry "HTTP <status>" so we can map nicely.
    const httpMatch = /^HTTP (\d{3})$/.exec(error.message);
    if (httpMatch) {
      const status = Number(httpMatch[1]);
      return HTTP_ERROR_LABEL[status] ?? `删除失败：HTTP ${status}`;
    }
    return "网络错误，请重试";
  }
  return "删除失败：未知错误";
}

export function PaperDeleteAction({
  paperId,
  paperTitle,
  draftCount,
  hasInsight,
  apiBaseUrl,
  apiKey,
  dataSource,
}: PaperDeleteActionProps) {
  const router = useRouter();
  const [status, setStatus] = useState<Status>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();
  const liveMode = dataSource === "http" && apiBaseUrl !== null;

  function handleClickDelete() {
    setErrorMessage(null);
    setStatus("confirming");
  }

  function handleCancel() {
    setStatus("idle");
    setErrorMessage(null);
  }

  function handleConfirm() {
    if (!liveMode) {
      setErrorMessage("演示模式不支持删除");
      setStatus("error");
      return;
    }
    setStatus("deleting");
    setErrorMessage(null);
    startTransition(async () => {
      try {
        const headers: Record<string, string> = { accept: "application/json" };
        if (apiKey) {
          headers.Authorization = `Bearer ${apiKey}`;
        }
        const url = `${apiBaseUrl!.replace(/\/+$/, "")}/papers/${paperId}`;
        const response = await fetch(url, { method: "DELETE", headers });
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        // Success — navigate away and refresh the list cache.
        router.push("/papers");
        router.refresh();
      } catch (error) {
        setErrorMessage(describeError(error));
        setStatus("error");
      }
    });
  }

  if (status === "idle") {
    return (
      <button
        type="button"
        onClick={handleClickDelete}
        disabled={!liveMode}
        className="action-button border border-[rgba(251,113,133,0.32)] bg-[rgba(251,113,133,0.08)] text-[color:var(--accent-rose)] hover:bg-[rgba(251,113,133,0.14)] disabled:cursor-not-allowed disabled:opacity-60"
        title={liveMode ? "永久删除此论文及其关联数据" : "演示模式不支持删除"}
      >
        删除
        <Trash2 className="h-4 w-4" aria-hidden="true" />
      </button>
    );
  }

  // confirming / deleting / error all render the inline danger region;
  // disabled state of buttons varies.
  const isDeleting = status === "deleting" || isPending;
  const insightCount = hasInsight ? 1 : 0;
  return (
    <div className="rounded-[1.25rem] border border-[rgba(251,113,133,0.32)] bg-[rgba(251,113,133,0.08)] p-4 text-[color:var(--accent-rose)]">
      <p className="text-sm font-semibold">确认删除？</p>
      <p className="mt-1 text-sm text-[color:var(--text-primary)]">
        将永久删除「{paperTitle.length > 30 ? `${paperTitle.slice(0, 30)}…` : paperTitle}」及{" "}
        {insightCount} 个洞察、{draftCount} 个草稿。该操作不可撤销。
      </p>
      {status === "error" && errorMessage ? (
        <p className="mt-3 text-sm font-medium text-[color:var(--accent-rose)]">{errorMessage}</p>
      ) : null}
      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={handleCancel}
          disabled={isDeleting}
          className="action-button action-button-secondary disabled:cursor-not-allowed disabled:opacity-60"
        >
          取消
        </button>
        <button
          type="button"
          onClick={handleConfirm}
          disabled={isDeleting}
          className="action-button bg-[color:var(--accent-rose)] text-[#1a0709] hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isDeleting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              删除中…
            </>
          ) : (
            <>
              确认删除
              <Trash2 className="h-4 w-4" aria-hidden="true" />
            </>
          )}
        </button>
      </div>
    </div>
  );
}
