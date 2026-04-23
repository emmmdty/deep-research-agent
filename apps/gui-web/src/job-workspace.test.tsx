import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { App } from "./App";

const jobResponse = {
  job_id: "job-123",
  topic: "Anthropic company profile",
  status: "completed",
  current_stage: "completed",
  created_at: "2026-04-23T10:00:00Z",
  updated_at: "2026-04-23T10:01:00Z",
  attempt_index: 1,
  retry_of: null,
  cancel_requested: false,
  source_profile: "company_trusted",
  budget: {},
  policy_overrides: {},
  connector_health: {},
  audit_gate_status: "passed",
  critical_claim_count: 2,
  blocked_critical_claim_count: 0,
  error: null,
  artifact_urls: {
    bundle: "/v1/research/jobs/job-123/bundle",
    report_html: "/v1/research/jobs/job-123/artifacts/report.html",
    report_bundle: "/v1/research/jobs/job-123/artifacts/report_bundle.json",
  },
};

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    headers: { "content-type": "application/json" },
    status: 200,
  });
}

beforeEach(() => {
  window.localStorage.clear();
});

afterEach(() => {
  vi.restoreAllMocks();
});

test("submits a local no-worker research job and records it in known jobs", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = String(input);
    if (url.endsWith("/v1/research/jobs/job-123/events?after_sequence=0")) {
      return jsonResponse({ job_id: "job-123", events: [] });
    }
    return jsonResponse(jobResponse);
  });

  render(<App />);

  fireEvent.change(screen.getByLabelText(/topic/i), { target: { value: "Anthropic company profile" } });
  fireEvent.change(screen.getByLabelText(/source profile/i), { target: { value: "company_trusted" } });
  fireEvent.click(screen.getByRole("button", { name: /submit local job/i }));

  await waitFor(() => expect(screen.getAllByText("job-123").length).toBeGreaterThan(0));

  expect(fetchMock).toHaveBeenCalledWith(
    "http://127.0.0.1:8000/v1/research/jobs",
    expect.objectContaining({
      method: "POST",
      body: expect.stringContaining('"start_worker":false'),
    }),
  );
  const detail = await screen.findByLabelText("Job detail");
  expect(within(detail).getByText(/audit gate/i)).toBeInTheDocument();
  expect(window.localStorage.getItem("dra.gui.knownJobs")).toContain("job-123");
});

test("loads job status, events, and bundle artifact from a manual job id", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = String(input);
    if (url.endsWith("/v1/research/jobs/job-123/events?after_sequence=0")) {
      return jsonResponse({
        job_id: "job-123",
        events: [
          {
            event_id: "evt-1",
            job_id: "job-123",
            sequence: 1,
            stage: "rendering",
            event_type: "bundle.emitted",
            timestamp: "2026-04-23T10:01:00Z",
            message: "Bundle emitted.",
            payload: {},
          },
        ],
      });
    }
    if (url.endsWith("/v1/research/jobs/job-123/bundle")) {
      return jsonResponse({
        job: { job_id: "job-123", status: "completed" },
        claims: [{ claim_id: "claim-1", text: "Grounded claim" }],
        sources: [{ source_id: "source-1", title: "Official source" }],
      });
    }
    return jsonResponse(jobResponse);
  });

  render(<App />);

  fireEvent.change(screen.getByLabelText(/manual job id/i), { target: { value: "job-123" } });
  fireEvent.click(screen.getByRole("button", { name: /load job/i }));

  const detail = await screen.findByLabelText("Job detail");
  await within(detail).findAllByText("completed");
  await within(detail).findByText(/Bundle emitted/i);

  fireEvent.click(screen.getByRole("button", { name: /load bundle/i }));

  await within(detail).findByText(/Grounded claim/i);
  expect(fetchMock).toHaveBeenCalledWith("http://127.0.0.1:8000/v1/research/jobs/job-123", expect.any(Object));
  await waitFor(() => expect(screen.getByText(/Official source/i)).toBeInTheDocument());
});
