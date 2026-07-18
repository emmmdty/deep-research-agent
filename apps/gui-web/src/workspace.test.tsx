import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { App } from "./App";

const topic = {
  topic_id: "top-1",
  tenant_id: "tenant-1",
  title: "事件图谱、Agent 与 LLM",
  conversation_id: "con-1",
  created_at: "2026-07-18T08:00:00Z",
  updated_at: "2026-07-18T08:00:00Z",
};

const run = {
  run_id: "run-1",
  research_job_id: "job-1",
  tenant_id: "tenant-1",
  topic_id: "top-1",
  conversation_id: "con-1",
  question: "三者如何相互促进？",
  status: "completed",
  config_version_id: "runtime-v1",
  snapshot_cutoff: "2026-07-18T08:10:00Z",
  cancel_requested: false,
  created_at: "2026-07-18T08:01:00Z",
  updated_at: "2026-07-18T08:10:00Z",
};

const bundle = {
  schema_version: "2.0",
  report_markdown:
    "# 事件图谱、Agent 与 LLM：融合研究报告\n\n## 执行摘要\n\n事件图谱可为 Agent 提供可追溯的长期状态。\n\n## 研究发现\n\n多 Agent 协作需要共享证据边界。",
  accepted_claims: [
    {
      claim_id: "claim-1",
      claim_text: "事件图谱可为 Agent 提供可追溯的长期状态。",
      status: "supported",
      evidence_spans: [
        {
          span_id: "span-1",
          document_id: "doc-1",
          title: "Graph-Augmented Agents",
          text: "Graphs preserve entity and event state across agent steps.",
          locator: { page: 4, section: "3.2" },
          source_url: "https://arxiv.org/abs/2601.00001",
        },
      ],
    },
  ],
  research_graph: {
    nodes: [
      { node_id: "claim-1", label: "图谱提供长期状态", kind: "claim", properties: {} },
      { node_id: "paper-1", label: "Graph-Augmented Agents", kind: "paper", properties: {} },
    ],
    edges: [{ edge_id: "edge-1", source_node_id: "paper-1", target_node_id: "claim-1", relation: "supports", evidence_span_ids: ["span-1"] }],
  },
  papers: [{ document_id: "doc-1", title: "Graph-Augmented Agents", year: 2026, trust_tier: 1 }],
};

const jsonResponse = (value: unknown, status = 200) =>
  new Response(status === 204 ? null : JSON.stringify(value), {
    status,
    headers: { "content-type": "application/json" },
  });

function mockProductApi() {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url = new URL(String(input), window.location.origin);
    const method = init?.method ?? "GET";
    if (url.pathname === "/v1/auth/session") return jsonResponse({ user: { user_id: "usr-1", tenant_id: "tenant-1", email: "researcher@example.test", role: "user" } });
    if (url.pathname === "/v1/topics" && method === "GET") return jsonResponse({ topics: [topic] });
    if (url.pathname === "/v1/topics/top-1" && method === "GET") return jsonResponse(topic);
    if (url.pathname === "/v1/topics/top-1/runs" && method === "GET") return jsonResponse({ runs: [run] });
    if (url.pathname === "/v1/topics/top-1/runs" && method === "POST") {
      return jsonResponse({ ...run, status: "created", run_id: "run-new" }, 202);
    }
    if (url.pathname === "/v1/runs/run-1" && method === "GET") return jsonResponse(run);
    if (url.pathname === "/v1/runs/run-1/bundle") return jsonResponse(bundle);
    if (url.pathname === "/v1/memory" && method === "GET") {
      return jsonResponse({
        memories: [
          {
            memory_id: "mem-1",
            scope: "user_preference",
            content: "优先阅读经过同行评审的论文",
            confidence: 0.9,
            status: "active",
            updated_at: "2026-07-18T08:00:00Z",
          },
        ],
      });
    }
    if (url.pathname === "/v1/memory/mem-1" && method === "DELETE") return jsonResponse(null, 204);
    if (url.pathname === "/v1/admin/models") {
      return jsonResponse({
        models: [
          {
            endpoint_id: "research-primary",
            base_url: "https://models.example.test/v1",
            model: "research-model",
            api_key: "[redacted]",
            enabled: true,
          },
        ],
      });
    }
    if (url.pathname === "/v1/admin/configs") {
      return jsonResponse({ configs: [{ version_id: "runtime-v1", config: {}, active: true }] });
    }
    if (url.pathname === "/v1/conversations/con-1/messages" && method === "POST") {
      const body = JSON.parse(String(init?.body));
      if (String(body.content).includes("完整") || body.refresh) {
        return jsonResponse({
          response_type: "research_job_started",
          brief: { brief_id: "brf-2", question: body.content, objectives: [body.content], constraints: {} },
          answer: null,
          clarification_questions: [],
          run_id: "run-new",
        }, 202);
      }
      return jsonResponse({
        response_type: "clarification_required",
        brief: { brief_id: "brf-1", question: body.content, objectives: [], constraints: {} },
        answer: null,
        clarification_questions: ["希望覆盖哪一段时间？", "是否只纳入同行评审论文？"],
        run_id: null,
      });
    }
    throw new Error(`Unhandled request: ${method} ${url.pathname}`);
  });
}

beforeEach(() => {
  window.history.pushState({}, "", "/topics/top-1");
  window.localStorage.clear();
  mockProductApi();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("research workspace", () => {
  test("submits a simple prompt and opens an editable clarification brief", async () => {
    render(<App />);

    fireEvent.change(await screen.findByLabelText("研究问题"), { target: { value: "研究三者关系" } });
    fireEvent.click(screen.getByRole("button", { name: "发送" }));

    expect(await screen.findByRole("heading", { name: "完善研究简报" })).toBeInTheDocument();
    const brief = screen.getByLabelText("研究问题简报");
    expect(brief).toHaveValue("研究三者关系");
    fireEvent.change(brief, { target: { value: "完整分析 2024 至 2026 年的三者关系" } });
    fireEvent.click(screen.getByRole("button", { name: "开始研究" }));
    expect(await screen.findByText("研究任务已启动")).toBeInTheDocument();
  });

  test("sends an explicit refresh request against the current topic", async () => {
    const fetchMock = vi.mocked(globalThis.fetch);
    render(<App />);

    fireEvent.change(await screen.findByLabelText("研究问题"), { target: { value: "完整更新最新进展" } });
    fireEvent.click(screen.getByRole("checkbox", { name: "刷新资料快照" }));
    fireEvent.click(screen.getByRole("button", { name: "发送" }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/v1/conversations/con-1/messages"),
        expect.objectContaining({ body: expect.stringContaining('"refresh":true') }),
      ),
    );
  });

  test("renders report markdown as semantic headings", async () => {
    window.history.pushState({}, "", "/topics/top-1/runs/run-1");
    render(<App />);

    expect(await screen.findByRole("heading", { name: "事件图谱、Agent 与 LLM：融合研究报告", level: 1 })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "执行摘要", level: 2 })).toBeInTheDocument();
    expect(screen.queryByRole("code")).not.toHaveTextContent("report_markdown");
  });

  test("connects a report claim to its evidence drawer", async () => {
    window.history.pushState({}, "", "/topics/top-1/runs/run-1");
    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: /查看论断 claim-1 的证据/ }));
    const drawer = await screen.findByRole("complementary", { name: "证据详情" });
    expect(within(drawer).getByText("Graph-Augmented Agents")).toBeInTheDocument();
    expect(within(drawer).getByText(/page 4/)).toBeInTheDocument();
  });

  test("selects graph evidence without exposing model reasoning", async () => {
    window.history.pushState({}, "", "/topics/top-1/runs/run-1");
    render(<App />);

    fireEvent.click(await screen.findByRole("tab", { name: "关系图" }));
    fireEvent.click(await screen.findByRole("button", { name: "Graph-Augmented Agents" }));
    expect(await screen.findByText("Graphs preserve entity and event state across agent steps.")).toBeInTheDocument();
    expect(screen.queryByText(/chain of thought|reasoning/i)).not.toBeInTheDocument();
  });

  test("deletes a governed memory after confirmation", async () => {
    window.history.pushState({}, "", "/memory");
    vi.spyOn(window, "confirm").mockReturnValue(true);
    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: "删除记忆" }));
    await waitFor(() => expect(screen.queryByText("优先阅读经过同行评审的论文")).not.toBeInTheDocument());
  });

  test("keeps administrator model secrets redacted", async () => {
    window.history.pushState({}, "", "/admin/models");
    render(<App />);

    expect(await screen.findByText("research-primary")).toBeInTheDocument();
    expect(screen.getByText("[redacted]")).toBeInTheDocument();
    expect(document.body.textContent).not.toContain("top-secret");
  });

  test("opens route navigation without covering the mobile workspace", async () => {
    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: "打开导航" }));
    const nav = screen.getByRole("navigation", { name: "移动导航" });
    expect(within(nav).getByRole("link", { name: "记忆" })).toHaveAttribute("href", "/memory");
    fireEvent.click(screen.getByRole("button", { name: "关闭导航" }));
    expect(screen.queryByRole("navigation", { name: "移动导航" })).not.toBeInTheDocument();
  });

  test("labels the V1 audit view as a current summary instead of a false snapshot comparison", async () => {
    window.history.pushState({}, "", "/topics/top-1/runs/run-1");
    render(<App />);

    fireEvent.click(await screen.findByRole("tab", { name: "变化" }));
    expect(await screen.findByText("当前审计摘要")).toBeInTheDocument();
    expect(screen.queryByText("与上一快照比较")).not.toBeInTheDocument();
  });
});

describe("run event stream", () => {
  class FakeEventSource {
    static instances: FakeEventSource[] = [];
    onopen: ((event: Event) => void) | null = null;
    onerror: ((event: Event) => void) | null = null;
    onmessage: ((event: MessageEvent) => void) | null = null;
    readonly listeners = new Map<string, Array<(event: MessageEvent) => void>>();
    readonly url: string;
    readonly withCredentials: boolean;
    closed = false;

    constructor(url: string | URL, init?: EventSourceInit) {
      this.url = String(url);
      this.withCredentials = Boolean(init?.withCredentials);
      FakeEventSource.instances.push(this);
    }

    addEventListener(type: string, listener: EventListenerOrEventListenerObject) {
      const callback = typeof listener === "function" ? listener : listener.handleEvent.bind(listener);
      const listeners = this.listeners.get(type) ?? [];
      listeners.push(callback as (event: MessageEvent) => void);
      this.listeners.set(type, listeners);
    }

    close() { this.closed = true; }

    emitError() { this.onerror?.(new Event("error")); }

    emit(type: string, payload: Record<string, unknown>, lastEventId = "2") {
      const event = new MessageEvent(type, { data: JSON.stringify(payload), lastEventId });
      for (const listener of this.listeners.get(type) ?? []) listener(event);
    }
  }

  test("mounts for a pending run and consumes a named terminal event to load the report", async () => {
    FakeEventSource.instances = [];
    vi.stubGlobal("EventSource", FakeEventSource);
    let completed = false;
    vi.mocked(globalThis.fetch).mockImplementation(async (input, init) => {
      const url = new URL(String(input), window.location.origin);
      const method = init?.method ?? "GET";
      if (url.pathname === "/v1/auth/session") return jsonResponse({ user: { user_id: "usr-1", role: "user" } });
      if (url.pathname === "/v1/topics") return jsonResponse({ topics: [topic] });
      if (url.pathname === "/v1/topics/top-1") return jsonResponse(topic);
      if (url.pathname === "/v1/topics/top-1/runs" && method === "GET") return jsonResponse({ runs: [{ ...run, status: completed ? "completed" : "running" }] });
      if (url.pathname === "/v1/runs/run-1") return jsonResponse({ ...run, status: completed ? "completed" : "running" });
      if (url.pathname === "/v1/runs/run-1/bundle") return jsonResponse(bundle);
      throw new Error(`Unhandled request: ${method} ${url.pathname}`);
    });
    window.history.pushState({}, "", "/topics/top-1/runs/run-1");
    render(<App />);

    expect(await screen.findByRole("heading", { name: "Agent 集群正在执行" })).toBeInTheDocument();
    expect(FakeEventSource.instances).toHaveLength(1);
    expect(FakeEventSource.instances[0].withCredentials).toBe(true);
    expect(FakeEventSource.instances[0].listeners.has("run.completed")).toBe(true);

    FakeEventSource.instances[0].emitError();
    expect(await screen.findByText("正在重新连接")).toBeInTheDocument();

    completed = true;
    FakeEventSource.instances[0].emit("run.completed", { terminal: true, status: "completed" });
    expect(await screen.findByRole("heading", { name: "事件图谱、Agent 与 LLM：融合研究报告" })).toBeInTheDocument();
    expect(FakeEventSource.instances[0].closed).toBe(true);
  });
});

describe("authentication boundary", () => {
  test("redirects an unauthenticated product route to login", async () => {
    vi.mocked(globalThis.fetch).mockResolvedValue(jsonResponse({ detail: "authentication required" }, 401));
    window.history.pushState({}, "", "/topics");
    render(<App />);

    expect(await screen.findByRole("heading", { name: "进入研究工作区" })).toBeInTheDocument();
    expect(window.location.pathname).toBe("/login");
  });

  test("revalidates the session after login before entering the product", async () => {
    let sessionReads = 0;
    vi.mocked(globalThis.fetch).mockImplementation(async (input, init) => {
      const url = new URL(String(input), window.location.origin);
      if (url.pathname === "/v1/auth/login" && init?.method === "POST") return jsonResponse({ user: { user_id: "usr-1", role: "user" }, csrf_token: "csrf-1" });
      if (url.pathname === "/v1/auth/session") { sessionReads += 1; return jsonResponse({ user: { user_id: "usr-1", role: "user" } }); }
      if (url.pathname === "/v1/topics") return jsonResponse({ topics: [] });
      throw new Error(`Unhandled request: ${url.pathname}`);
    });
    window.history.pushState({}, "", "/login");
    render(<App />);

    fireEvent.change(screen.getByLabelText("邮箱"), { target: { value: "researcher@example.test" } });
    fireEvent.change(screen.getByLabelText("密码"), { target: { value: "correct horse battery staple" } });
    fireEvent.click(screen.getByRole("button", { name: /登录/ }));

    expect(await screen.findByRole("heading", { name: /从问题开始/ })).toBeInTheDocument();
    expect(sessionReads).toBeGreaterThan(0);
  });
});
