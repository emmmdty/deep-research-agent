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
  claim_graph: {
    nodes: [
      { id: "claim-1", label: "图谱提供长期状态", kind: "claim", evidence_ids: ["span-1"] },
      { id: "paper-1", label: "Graph-Augmented Agents", kind: "paper", evidence_ids: ["span-1"] },
    ],
    edges: [{ source: "paper-1", target: "claim-1", label: "supports" }],
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
    const url = new URL(String(input));
    const method = init?.method ?? "GET";
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
    fireEvent.click(await screen.findByRole("button", { name: "图谱提供长期状态" }));
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

    fireEvent.click(screen.getByRole("button", { name: "打开导航" }));
    const nav = screen.getByRole("navigation", { name: "移动导航" });
    expect(within(nav).getByRole("link", { name: "记忆" })).toHaveAttribute("href", "/memory");
    fireEvent.click(screen.getByRole("button", { name: "关闭导航" }));
    expect(screen.queryByRole("navigation", { name: "移动导航" })).not.toBeInTheDocument();
  });
});

describe("run event stream", () => {
  test("recovers from a transient SSE error and applies the next event", async () => {
    window.history.pushState({}, "", "/topics/top-1/runs/run-1");
    render(<App />);

    expect(await screen.findByText("实时连接")).toBeInTheDocument();
    window.dispatchEvent(new CustomEvent("dra:test-stream-error"));
    expect(await screen.findByText("正在重新连接")).toBeInTheDocument();
    window.dispatchEvent(
      new CustomEvent("dra:test-stream-event", {
        detail: { event_id: "2", event_type: "worker.completed", payload: { terminal: false, source_count: 12 } },
      }),
    );
    expect(await screen.findByText("已恢复连接")).toBeInTheDocument();
  });
});
