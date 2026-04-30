import { parseApiEnvelope } from "../../api-contracts.ts";

interface FetchResponseLike {
  ok: boolean;
  status: number;
  json(): Promise<unknown>;
}

export type FetchLike = (input: string | URL, init?: RequestInit) => Promise<FetchResponseLike>;

export interface HttpDataSourceOptions {
  baseUrl: string;
  fetch?: FetchLike;
}

export interface HttpQueryParams {
  [key: string]: boolean | number | string | null | undefined;
}

function resolveFetch(fetchImplementation?: FetchLike): FetchLike {
  if (fetchImplementation) {
    return fetchImplementation;
  }

  if (typeof fetch !== "function") {
    throw new Error("Global fetch is not available for HTTP data source mode.");
  }

  return fetch as FetchLike;
}

export function buildRequestUrl(baseUrl: string, path: string, query: HttpQueryParams = {}): string {
  const normalizedBaseUrl = `${baseUrl.replace(/\/+$/, "")}/`;
  const normalizedPath = path.replace(/^\//, "");
  const url = new URL(normalizedPath, normalizedBaseUrl);

  for (const [key, value] of Object.entries(query)) {
    if (value === null || value === undefined) {
      continue;
    }

    url.searchParams.set(key, String(value));
  }

  // Use %20 for spaces instead of +
  return url.toString().replace(/\+/g, "%20");
}

export function createHttpClient(options: HttpDataSourceOptions) {
  const fetchImplementation = resolveFetch(options.fetch);

  return {
    buildUrl(path: string, query?: HttpQueryParams): string {
      return buildRequestUrl(options.baseUrl, path, query);
    },
    async get<TData>(path: string, query?: HttpQueryParams): Promise<TData> {
      const requestUrl = buildRequestUrl(options.baseUrl, path, query);
      const response = await fetchImplementation(requestUrl, {
        method: "GET",
        headers: {
          accept: "application/json",
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP request failed with status ${response.status} for ${requestUrl}`);
      }

      return parseApiEnvelope<TData>(await response.json()).data;
    },
    async post<TData>(path: string, body?: unknown): Promise<TData> {
      const requestUrl = buildRequestUrl(options.baseUrl, path);
      const response = await fetchImplementation(requestUrl, {
        method: "POST",
        headers: {
          accept: "application/json",
          "content-type": "application/json",
        },
        body: body === undefined ? undefined : JSON.stringify(body),
      });

      if (!response.ok) {
        throw new Error(`HTTP request failed with status ${response.status} for ${requestUrl}`);
      }

      return parseApiEnvelope<TData>(await response.json()).data;
    },
  };
}
