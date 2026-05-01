"use client";

import { Bell, FileText, Play, RefreshCw, XCircle } from "lucide-react";
import { useEffect, useMemo, useState, useTransition } from "react";

import { StatusBadge } from "@/components/status-badge";
import { parseApiEnvelope } from "@/lib/api-contracts";
import { formatDateTime } from "@/lib/format";
import type { ApiDataSource } from "@/lib/api-contracts";
import type { PipelineTaskCreateInput, PipelineTaskItem, PipelineTaskStatus } from "@/lib/types";

interface PipelineTaskControlProps {
  apiBaseUrl: string | null;
  apiKey: string | null;
  dataSource: ApiDataSource;
  initialTasks: PipelineTaskItem[];
}

const statusTone: Record<PipelineTaskStatus, "success" | "danger" | "warning" | "info" | "neutral"> = {
  queued: "info",
  running: "warning",
  cancelling: "warning",
  success: "success",
  failed: "danger",
  cancelled: "neutral",
};

const statusLabel: Record<PipelineTaskStatus, string> = {
  queued: "排队中",
  running: "运行中",
  cancelling: "取消中",
  success: "成功",
  failed: "失败",
  cancelled: "已取消",
};

function summarizeTask(task: PipelineTaskItem): string {
  const crawl = task.result.crawl as { totalFetched?: number; totalNew?: number } | undefined;
  const editorial = task.result.editorial as { generated?: number } | undefined;
  const notify = task.result.notify as { succeeded?: number; failed?: number; skipped?: string } | undefined;

  const parts = [];
  if (crawl) {
    parts.push(`抓取 ${crawl.totalFetched ?? 0}，新增 ${crawl.totalNew ?? 0}`);
  }
  if (editorial) {
    parts.push(`草稿 ${editorial.generated ?? 0}`);
  }
  if (notify?.skipped) {
    parts.push("通知跳过");
  } else if (notify) {
    parts.push(`通知成功 ${notify.succeeded ?? 0}，失败 ${notify.failed ?? 0}`);
  }
  return parts.length > 0 ? parts.join(" · ") : "等待执行结果";
}

function buildTaskUrl(apiBaseUrl: string, path: string): string {
  return `${apiBaseUrl.replace(/\/+$/, "")}/${path.replace(/^\/+/, "")}`;
}

async function requestTask<TData>(
  apiBaseUrl: string,
  apiKey: string | null,
  path: string,
  init?: RequestInit,
): Promise<TData> {
  const headers: Record<string, string> = {
    accept: "application/json",
  };
  if (init?.body) {
    headers["content-type"] = "application/json";
  }
  if (apiKey) {
    headers.Authorization = `Bearer ${apiKey}`;
  }
  const response = await fetch(buildTaskUrl(apiBaseUrl, path), {
    ...init,
    headers,
  });
  if (!response.ok) {
    throw new Error(`请求失败：${response.status}`);
  }
  return parseApiEnvelope<TData>(await response.json()).data;
}

function createDemoTask(input: PipelineTaskCreateInput): PipelineTaskItem {
  return {
    taskId: Date.now(),
    taskType: "full_pipeline",
    status: "queued",
    currentStage: "queued",
    progressCurrent: 0,
    progressTotal: 3,
    requestedBy: "demo-operator",
    parameters: {
      notify: input.notify,
      editorialLimit: input.editorialLimit,
    },
    result: {},
    errorMessage: null,
    createdAt: new Date().toISOString(),
    startedAt: null,
    finishedAt: null,
  };
}

export function PipelineTaskControl({ apiBaseUrl, apiKey, dataSource, initialTasks }: PipelineTaskControlProps) {
  const [tasks, setTasks] = useState(initialTasks);
  const [notify, setNotify] = useState(true);
  const [editorialLimit, setEditorialLimit] = useState(3);
  const [message, setMessage] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const activeTask = useMemo(
    () => tasks.find((task) => task.status === "queued" || task.status === "running") ?? null,
    [tasks],
  );

  useEffect(() => {
    if (!activeTask) {
      return;
    }
    const timer = window.setInterval(async () => {
      if (dataSource !== "http" || !apiBaseUrl) {
        return;
      }
      const latest = await requestTask<PipelineTaskItem>(apiBaseUrl, apiKey, `pipeline/tasks/${activeTask.taskId}`);
      if (!latest) {
        return;
      }
      setTasks((current) => current.map((task) => (task.taskId === latest.taskId ? latest : task)));
    }, 4000);
    return () => window.clearInterval(timer);
  }, [activeTask, apiBaseUrl, apiKey, dataSource]);

  function handleStart() {
    setMessage(null);
    startTransition(async () => {
      try {
        const input: PipelineTaskCreateInput = {
          taskType: "full_pipeline",
          notify,
          editorialLimit,
        };
        const task =
          dataSource === "http" && apiBaseUrl
            ? await requestTask<PipelineTaskItem>(apiBaseUrl, apiKey, "pipeline/tasks", {
                method: "POST",
                body: JSON.stringify(input),
              })
            : createDemoTask(input);
        setTasks((current) => [task, ...current.filter((item) => item.taskId !== task.taskId)].slice(0, 8));
        setMessage(`任务 #${task.taskId} 已提交`);
      } catch (error) {
        setMessage(error instanceof Error ? error.message : "启动任务失败");
      }
    });
  }

  function handleCancel(taskId: number) {
    setMessage(null);
    startTransition(async () => {
      try {
        const existing = tasks.find((item) => item.taskId === taskId);
        // queued 任务后端会直接转 cancelled；running 任务转 cancelling，
        // 由 worker 在下一个检查点写入终态。前端依赖后端返回的 status，
        // demo 模式下按当前状态推算：running → cancelling，其它 → cancelled。
        const optimisticStatus: PipelineTaskStatus =
          existing?.status === "running" ? "cancelling" : "cancelled";
        const task =
          dataSource === "http" && apiBaseUrl
            ? await requestTask<PipelineTaskItem>(apiBaseUrl, apiKey, `pipeline/tasks/${taskId}/cancel`, {
                method: "POST",
              })
            : ({
                ...existing,
                taskId,
                status: optimisticStatus,
                currentStage: optimisticStatus === "cancelled" ? "done" : existing?.currentStage ?? "crawl",
                finishedAt: optimisticStatus === "cancelled" ? new Date().toISOString() : null,
              } as PipelineTaskItem);
        setTasks((current) => current.map((item) => (item.taskId === task.taskId ? task : item)));
        setMessage(
          task.status === "cancelling"
            ? `任务 #${task.taskId} 已请求取消，等待 worker 在下一阶段间隙退出`
            : `任务 #${task.taskId} 已取消`,
        );
      } catch (error) {
        setMessage(error instanceof Error ? error.message : "取消任务失败");
      }
    });
  }

  return (
    <div className="space-y-5">
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-end">
        <div className="grid gap-4 sm:grid-cols-2">
          <label className="flex min-h-24 flex-col justify-between rounded-[1.2rem] border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.55)] p-4">
            <span className="flex items-center gap-2 text-sm font-semibold text-white">
              <Bell className="h-4 w-4 text-[color:var(--accent-blue)]" aria-hidden="true" />
              飞书通知
            </span>
            <span className="mt-3 inline-flex items-center gap-3 text-sm subtle-copy">
              <input
                type="checkbox"
                checked={notify}
                onChange={(event) => setNotify(event.currentTarget.checked)}
                className="h-4 w-4 accent-[color:var(--accent-blue)]"
              />
              抓取完成后发送待通知论文
            </span>
          </label>

          <label className="flex min-h-24 flex-col justify-between rounded-[1.2rem] border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.55)] p-4">
            <span className="flex items-center gap-2 text-sm font-semibold text-white">
              <FileText className="h-4 w-4 text-[color:var(--accent-green)]" aria-hidden="true" />
              草稿数量
            </span>
            <input
              type="number"
              min={1}
              max={20}
              value={editorialLimit}
              onChange={(event) => setEditorialLimit(Math.max(1, Number(event.currentTarget.value) || 1))}
              className="mt-3 h-10 rounded-[0.8rem] border border-[color:var(--border-subtle)] bg-[rgba(15,23,42,0.75)] px-3 text-sm text-white outline-none focus:border-[color:var(--accent-blue)]"
            />
          </label>
        </div>

        <button
          type="button"
          onClick={handleStart}
          disabled={isPending}
          className="inline-flex h-11 items-center justify-center gap-2 rounded-[0.9rem] bg-[color:var(--accent-blue)] px-5 text-sm font-semibold text-slate-950 transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isPending ? <RefreshCw className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Play className="h-4 w-4" aria-hidden="true" />}
          启动完整流水线
        </button>
      </div>

      {message ? <p className="text-sm subtle-copy">{message}</p> : null}

      <ol className="space-y-3">
        {tasks.slice(0, 6).map((task) => (
          <li key={task.taskId} className="rounded-[1.2rem] border border-[color:var(--border-subtle)] bg-[rgba(7,17,31,0.55)] p-4">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge label={statusLabel[task.status]} tone={statusTone[task.status]} />
                  <span className="text-sm font-semibold text-white">任务 #{task.taskId}</span>
                  <span className="text-xs text-[color:var(--text-dim)]">{task.currentStage}</span>
                </div>
                <p className="mt-2 text-sm subtle-copy">{summarizeTask(task)}</p>
                <p className="mt-2 text-xs text-[color:var(--text-dim)]">
                  {formatDateTime(task.createdAt)}
                  {task.errorMessage ? ` · ${task.errorMessage}` : ""}
                </p>
              </div>
              {task.status === "queued" || task.status === "running" ? (
                <button
                  type="button"
                  onClick={() => handleCancel(task.taskId)}
                  disabled={isPending}
                  className="inline-flex h-9 items-center justify-center gap-2 rounded-[0.8rem] border border-[rgba(251,113,133,0.28)] px-3 text-sm font-semibold text-[color:var(--accent-rose)] transition hover:bg-[rgba(251,113,133,0.1)] disabled:cursor-not-allowed disabled:opacity-60"
                  title={task.status === "running" ? "向 worker 发送取消信号，将在下一阶段间隙生效" : "取消排队中的任务"}
                >
                  <XCircle className="h-4 w-4" aria-hidden="true" />
                  取消
                </button>
              ) : task.status === "cancelling" ? (
                <button
                  type="button"
                  disabled
                  className="inline-flex h-9 items-center justify-center gap-2 rounded-[0.8rem] border border-[color:var(--border-subtle)] px-3 text-sm font-semibold text-[color:var(--text-dim)] opacity-70"
                  title="已请求取消，等待 worker 完成当前阶段"
                >
                  <XCircle className="h-4 w-4" aria-hidden="true" />
                  取消中…
                </button>
              ) : null}
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
