import { expect, test } from "vitest";

import { buildApiUrl, getDefaultApiBaseUrl } from "./client";

test("uses the local FastAPI base URL by default", () => {
  expect(getDefaultApiBaseUrl()).toBe("http://127.0.0.1:8000");
});

test("builds stable local API URLs without duplicate slashes", () => {
  expect(buildApiUrl("http://127.0.0.1:8000/", "/v1/research/jobs")).toBe(
    "http://127.0.0.1:8000/v1/research/jobs",
  );
});
