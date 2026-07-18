import { fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";

import { App } from "./App";

afterEach(() => vi.restoreAllMocks());

test("renders the evidence research product navigation", async () => {
  window.history.pushState({}, "", "/topics");
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const pathname = new URL(String(input), window.location.origin).pathname;
    if (pathname === "/v1/auth/session") return new Response(JSON.stringify({ user: { user_id: "usr-1", role: "user" } }), { status: 200, headers: { "content-type": "application/json" } });
    return new Response(JSON.stringify({ topics: [] }), { status: 200, headers: { "content-type": "application/json" } });
  });
  render(<App />);

  expect(await screen.findByRole("link", { name: "研究" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "记忆" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "管理" })).toBeInTheDocument();
  expect(await screen.findByRole("heading", { name: /从问题开始/ })).toBeInTheDocument();
  expect(await screen.findByText("从一个研究问题开始")).toBeInTheDocument();
});

test("shows local registration when the API enables it", async () => {
  window.history.pushState({}, "", "/login");
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const pathname = new URL(String(input), window.location.origin).pathname;
    if (pathname === "/v1/auth/session") return new Response(JSON.stringify({ detail: "authentication required" }), { status: 401 });
    if (pathname === "/v1/auth/registration-status") return new Response(JSON.stringify({ enabled: true }), { status: 200, headers: { "content-type": "application/json" } });
    return new Response(JSON.stringify({}), { status: 200, headers: { "content-type": "application/json" } });
  });
  render(<App />);

  expect(await screen.findByRole("heading", { name: "进入研究工作区" })).toBeInTheDocument();
  fireEvent.click(await screen.findByRole("button", { name: /注册新账号/ }));
  expect(await screen.findByRole("heading", { name: "创建研究账号" })).toBeInTheDocument();
  expect(screen.getByLabelText("密码")).toHaveAttribute("minlength", "12");
});
