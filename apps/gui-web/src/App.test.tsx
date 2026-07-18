import { render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { App } from "./App";

afterEach(() => vi.restoreAllMocks());

test("renders the evidence research product navigation", async () => {
  window.history.pushState({}, "", "/topics");
  vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ topics: [] }), { status: 200, headers: { "content-type": "application/json" } }));
  render(<App />);

  expect(screen.getByRole("link", { name: "研究" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "记忆" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "管理" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: /从问题开始/ })).toBeInTheDocument();
  expect(await screen.findByText("从一个研究问题开始")).toBeInTheDocument();
});
