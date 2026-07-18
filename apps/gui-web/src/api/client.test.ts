import { expect, test } from "vitest";

import { buildApiUrl, getDefaultApiBaseUrl } from "./client";

test("uses the same origin by default so the Vite and deployment proxies carry auth cookies", () => {
  expect(getDefaultApiBaseUrl()).toBe("");
  expect(buildApiUrl(getDefaultApiBaseUrl(), "/v1/topics")).toBe("/v1/topics");
});

test("builds stable local API URLs without duplicate slashes", () => {
  expect(buildApiUrl("http://127.0.0.1:8000/", "/v1/research/jobs")).toBe(
    "http://127.0.0.1:8000/v1/research/jobs",
  );
});
