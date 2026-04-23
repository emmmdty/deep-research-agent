import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";

import { App } from "./App";

test("renders the operator navigation and local API boundary", () => {
  render(<App />);

  expect(screen.getByRole("link", { name: /jobs/i })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /artifacts/i })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /benchmarks/i })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /docs/i })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /settings/i })).toBeInTheDocument();
  expect(screen.getByText(/local fastapi/i)).toBeInTheDocument();
});
