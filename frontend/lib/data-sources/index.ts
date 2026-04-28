import type { RuntimeConfig } from "../runtime-config.ts";
import { resolveRuntimeConfig } from "../runtime-config.ts";
import { demoNotificationsDataSource, type NotificationsDataSource } from "./demo/notifications.ts";
import { demoPapersDataSource, type PapersDataSource } from "./demo/papers.ts";
import { demoPipelineDataSource, type PipelineDataSource } from "./demo/pipeline.ts";
import { createHttpNotificationsDataSource } from "./http/notifications.ts";
import { createHttpPapersDataSource } from "./http/papers.ts";
import { createHttpPipelineDataSource } from "./http/pipeline.ts";
import type { FetchLike } from "./http/shared.ts";

export interface ResolvedDataSources {
  papers: PapersDataSource;
  notifications: NotificationsDataSource;
  pipeline: PipelineDataSource;
}

interface ResolveDataSourcesOptions {
  fetch?: FetchLike;
}

function requireApiBaseUrl(config: RuntimeConfig): string {
  if (!config.apiBaseUrl) {
    throw new Error("HTTP data source mode requires an API base URL via PAPERCLAW_API_BASE_URL.");
  }

  return config.apiBaseUrl;
}

export function resolveDataSources(
  config: RuntimeConfig = resolveRuntimeConfig(),
  options: ResolveDataSourcesOptions = {},
): ResolvedDataSources {
  if (config.dataSource === "http") {
    const baseUrl = requireApiBaseUrl(config);

    return {
      papers: createHttpPapersDataSource({
        baseUrl,
        fetch: options.fetch,
      }),
      notifications: createHttpNotificationsDataSource({
        baseUrl,
        fetch: options.fetch,
      }),
      pipeline: createHttpPipelineDataSource({
        baseUrl,
        fetch: options.fetch,
      }),
    };
  }

  return {
    papers: demoPapersDataSource,
    notifications: demoNotificationsDataSource,
    pipeline: demoPipelineDataSource,
  };
}

export const runtimeDataSources = resolveDataSources();
