import { render, screen, within } from "@testing-library/react";
import { expect, test } from "vitest";

import { App } from "./App";

test("shows native benchmark gate, regression suites, and reviewer artifact links", () => {
  render(<App />);

  const consoleRegion = screen.getByLabelText("Benchmark console");

  expect(within(consoleRegion).getByText("smoke_local")).toBeInTheDocument();
  expect(within(consoleRegion).getByText("regression_local")).toBeInTheDocument();
  expect(within(consoleRegion).getByText(/authoritative merge gate/i)).toBeInTheDocument();
  expect(within(consoleRegion).getByText(/phase5_local_smoke/i)).toBeInTheDocument();

  for (const suiteName of ["company12", "industry12", "trusted8", "file8", "recovery6"]) {
    expect(within(consoleRegion).getAllByText(suiteName).length).toBeGreaterThan(0);
  }

  expect(within(consoleRegion).getAllByText(/1 -> 12/).length).toBe(2);
  expect(within(consoleRegion).getAllByText("passed").length).toBeGreaterThan(4);

  const scorecard = within(consoleRegion).getByRole("link", { name: /native scorecard/i });
  const casebook = within(consoleRegion).getByRole("link", { name: /native casebook/i });
  const manifest = within(consoleRegion).getByRole("link", { name: /regression manifest/i });

  expect(scorecard).toHaveAttribute("href", expect.stringContaining("docs/benchmarks/native/NATIVE_SCORECARD.md"));
  expect(casebook).toHaveAttribute("href", expect.stringContaining("docs/benchmarks/native/CASEBOOK.md"));
  expect(manifest).toHaveAttribute("href", expect.stringContaining("evals/reports/native_regression/release_manifest.json"));
});
