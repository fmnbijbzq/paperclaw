import type { ApiDataSource } from "./api-contracts.ts";

export interface RuntimeConfig {
  dataSource: ApiDataSource;
  apiBaseUrl: string | null;
}

export interface RuntimeConfigEnvironment {
  [key: string]: string | undefined;
  PAPERCLAW_DATA_SOURCE?: string;
  PAPERCLAW_API_BASE_URL?: string;
  NEXT_PUBLIC_API_BASE_URL?: string;
}

function normalizeDataSource(value: string | undefined): ApiDataSource {
  return value === "http" ? "http" : "demo";
}

function normalizeApiBaseUrl(value: string | undefined): string | null {
  const normalizedValue = value?.trim();

  if (!normalizedValue) {
    return null;
  }

  return normalizedValue.replace(/\/+$/, "");
}

export function resolveRuntimeConfig(env: RuntimeConfigEnvironment = process.env): RuntimeConfig {
  const apiBaseUrl = normalizeApiBaseUrl(env.PAPERCLAW_API_BASE_URL ?? env.NEXT_PUBLIC_API_BASE_URL);
  const configuredDataSource = env.PAPERCLAW_DATA_SOURCE;

  return {
    dataSource: configuredDataSource ? normalizeDataSource(configuredDataSource) : apiBaseUrl ? "http" : "demo",
    apiBaseUrl,
  };
}
