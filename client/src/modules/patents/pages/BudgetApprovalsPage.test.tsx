import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import BudgetApprovalsPage from "./BudgetApprovalsPage";

function renderWithClient(ui: ReactNode) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MantineProvider>
        <MemoryRouter>{ui}</MemoryRouter>
      </MantineProvider>
    </QueryClientProvider>,
  );
}

describe("BudgetApprovalsPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders loading state", () => {
    vi.spyOn(http, "get").mockReturnValue(new Promise(() => {}));
    renderWithClient(<BudgetApprovalsPage />);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("renders empty state", async () => {
    vi.spyOn(http, "get").mockResolvedValueOnce({
      data: { results: [], next: null, previous: null },
    });
    renderWithClient(<BudgetApprovalsPage />);
    await waitFor(() => {
      expect(screen.getByText("No pending budgets")).toBeInTheDocument();
    });
  });

  it("renders budget approval controls", async () => {
    vi.spyOn(http, "get").mockResolvedValueOnce({
      data: {
        results: [
          {
            id: 8,
            application_number: "PMS-2026-008",
            title: "Microfluidic Chip",
            status: "BUDGET_PENDING",
          },
        ],
        next: null,
        previous: null,
      },
    });

    renderWithClient(<BudgetApprovalsPage />);
    await waitFor(() => {
      expect(screen.getByText("Microfluidic Chip")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Approve budget for Microfluidic Chip" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reject budget for Microfluidic Chip" })).toBeInTheDocument();
  });
});
