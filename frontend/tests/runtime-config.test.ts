import assert from "node:assert/strict";
import test from "node:test";

import { demoNotificationsDataSource } from "../lib/data-sources/demo/notifications.ts";
import { demoPapersDataSource } from "../lib/data-sources/demo/papers.ts";
import { demoPipelineDataSource } from "../lib/data-sources/demo/pipeline.ts";
import { resolveDataSources } from "../lib/data-sources/index.ts";
import { resolveRuntimeConfig } from "../lib/runtime-config.ts";

test("resolveRuntimeConfig defaults to demo mode with no API base URL", () => {
  const config = resolveRuntimeConfig({});

  assert.deepEqual(config, {
    dataSource: "demo",
    apiBaseUrl: null,
    apiKey: null,
  });
});

test("resolveRuntimeConfig accepts HTTP mode and normalizes the API base URL", () => {
  const config = resolveRuntimeConfig({
    PAPERCLAW_DATA_SOURCE: "http",
    PAPERCLAW_API_BASE_URL: "https://paperclaw.example/api/",
  });

  assert.deepEqual(config, {
    dataSource: "http",
    apiBaseUrl: "https://paperclaw.example/api",
    apiKey: null,
  });
});

test("resolveRuntimeConfig treats NEXT_PUBLIC_API_BASE_URL as an HTTP shortcut", () => {
  const config = resolveRuntimeConfig({
    NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000/",
  });

  assert.deepEqual(config, {
    dataSource: "http",
    apiBaseUrl: "http://localhost:8000",
    apiKey: null,
  });
});

test("resolveRuntimeConfig falls back to demo mode for unsupported values", () => {
  const config = resolveRuntimeConfig({
    PAPERCLAW_DATA_SOURCE: "staging",
    PAPERCLAW_API_BASE_URL: "   ",
  });

  assert.deepEqual(config, {
    dataSource: "demo",
    apiBaseUrl: null,
    apiKey: null,
  });
});

test("resolveRuntimeConfig reads apiKey from NEXT_PUBLIC_API_KEY", () => {
  const config = resolveRuntimeConfig({
    NEXT_PUBLIC_API_BASE_URL: "http://localhost:8000",
    NEXT_PUBLIC_API_KEY: "the-key",
  });

  assert.deepEqual(config, {
    dataSource: "http",
    apiBaseUrl: "http://localhost:8000",
    apiKey: "the-key",
  });
});

test("resolveDataSources returns demo implementations by default", () => {
  const dataSources = resolveDataSources({
    dataSource: "demo",
    apiBaseUrl: null,
    apiKey: null,
  });

  assert.equal(dataSources.papers, demoPapersDataSource);
  assert.equal(dataSources.notifications, demoNotificationsDataSource);
  assert.equal(dataSources.pipeline, demoPipelineDataSource);
});

test("resolveDataSources switches to HTTP implementations when configured", () => {
  const dataSources = resolveDataSources({
    dataSource: "http",
    apiBaseUrl: "https://paperclaw.example/api",
    apiKey: null,
  });

  assert.notEqual(dataSources.papers, demoPapersDataSource);
  assert.notEqual(dataSources.notifications, demoNotificationsDataSource);
  assert.notEqual(dataSources.pipeline, demoPipelineDataSource);
  assert.equal(typeof dataSources.papers.listPapers, "function");
  assert.equal(typeof dataSources.notifications.listNotifications, "function");
  assert.equal(typeof dataSources.pipeline.listPipelineStages, "function");
});

test("resolveDataSources rejects HTTP mode without an API base URL", () => {
  assert.throws(
    () =>
      resolveDataSources({
        dataSource: "http",
        apiBaseUrl: null,
        apiKey: null,
      }),
    /API base URL/i,
  );
});
