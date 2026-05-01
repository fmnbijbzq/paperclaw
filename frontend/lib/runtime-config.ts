import type { ApiDataSource } from "./api-contracts.ts";

export interface RuntimeConfig {
  dataSource: ApiDataSource;
  apiBaseUrl: string | null;
  apiKey: string | null;
}

export interface RuntimeConfigEnvironment {
  [key: string]: string | undefined;
  PAPERCLAW_DATA_SOURCE?: string;
  PAPERCLAW_API_BASE_URL?: string;
  PAPERCLAW_API_KEY?: string;
  NEXT_PUBLIC_API_BASE_URL?: string;
  NEXT_PUBLIC_API_KEY?: string;
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

function normalizeApiKey(value: string | undefined): string | null {
  const trimmed = value?.trim();
  return trimmed ? trimmed : null;
}

export function resolveRuntimeConfig(env: RuntimeConfigEnvironment = process.env): RuntimeConfig {
  const apiBaseUrl = normalizeApiBaseUrl(env.PAPERCLAW_API_BASE_URL ?? env.NEXT_PUBLIC_API_BASE_URL);
  const apiKey = normalizeApiKey(env.PAPERCLAW_API_KEY ?? env.NEXT_PUBLIC_API_KEY);
  const configuredDataSource = env.PAPERCLAW_DATA_SOURCE;

  return {
    dataSource: configuredDataSource ? normalizeDataSource(configuredDataSource) : apiBaseUrl ? "http" : "demo",
    apiBaseUrl,
    apiKey,
  };
}
