import type { RuntimeConfig } from "../runtime-config.ts";
import { resolveRuntimeConfig } from "../runtime-config.ts";
import { demoNotificationsDataSource, type NotificationsDataSource } from "./demo/notifications.ts";
import { demoPapersDataSource, type PapersDataSource } from "./demo/papers.ts";
import { demoPipelineDataSource, type PipelineDataSource } from "./demo/pipeline.ts";
import { demoDraftsDataSource, type DraftsDataSource } from "./demo/drafts.ts";
import { demoExportsDataSource, type ExportsDataSource } from "./demo/exports.ts";
import { createHttpNotificationsDataSource } from "./http/notifications.ts";
import { createHttpPapersDataSource } from "./http/papers.ts";
import { createHttpPipelineDataSource } from "./http/pipeline.ts";
import { createHttpDraftsDataSource } from "./http/drafts.ts";
import { createHttpExportsDataSource } from "./http/exports.ts";
import type { FetchLike } from "./http/shared.ts";

export interface ResolvedDataSources {
  papers: PapersDataSource;
  notifications: NotificationsDataSource;
  pipeline: PipelineDataSource;
  drafts: DraftsDataSource;
  exports: ExportsDataSource;
}

interface ResolveDataSourcesOptions {
  fetch?: FetchLike;
}

function requireApiBaseUrl(config: RuntimeConfig): string {
  if (!config.apiBaseUrl) {
    throw new Error("HTTP data source mode requires an API base URL via PAPERCLAW_API_BASE_URL or NEXT_PUBLIC_API_BASE_URL.");
  }

  return config.apiBaseUrl;
}

export function resolveDataSources(
  config: RuntimeConfig = resolveRuntimeConfig(),
  options: ResolveDataSourcesOptions = {},
): ResolvedDataSources {
  if (config.dataSource === "http") {
    const baseUrl = requireApiBaseUrl(config);
    const apiKey = config.apiKey;

    return {
      papers: createHttpPapersDataSource({
        baseUrl,
        apiKey,
        fetch: options.fetch,
      }),
      notifications: createHttpNotificationsDataSource({
        baseUrl,
        apiKey,
        fetch: options.fetch,
      }),
      pipeline: createHttpPipelineDataSource({
        baseUrl,
        apiKey,
        fetch: options.fetch,
      }),
      drafts: createHttpDraftsDataSource({
        baseUrl,
        apiKey,
        fetch: options.fetch,
      }),
      exports: createHttpExportsDataSource({
        baseUrl,
        apiKey,
        fetch: options.fetch,
      }),
    };
  }

  return {
    papers: demoPapersDataSource,
    notifications: demoNotificationsDataSource,
    pipeline: demoPipelineDataSource,
    drafts: demoDraftsDataSource,
    exports: demoExportsDataSource,
  };
}

export const runtimeDataSources = resolveDataSources();
