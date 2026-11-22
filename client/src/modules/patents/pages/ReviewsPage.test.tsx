import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import ReviewsPage from "./ReviewsPage";

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

describe("ReviewsPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders loading state", () => {
    vi.spyOn(http, "get").mockReturnValue(new Promise(() => {}));
    renderWithClient(<ReviewsPage />);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("renders empty state when no applications await review", async () => {
    vi.spyOn(http, "get").mockResolvedValueOnce({
      data: { results: [], next: null, previous: null },
    });
    renderWithClient(<ReviewsPage />);
    await waitFor(() => {
      expect(screen.getByText("Review queue empty")).toBeInTheDocument();
    });
  });

  it("renders error state on 500", async () => {
    vi.spyOn(http, "get").mockRejectedValueOnce(new Error("Database connection error"));
    renderWithClient(<ReviewsPage />);
    await waitFor(() => {
      expect(screen.getByText("Could not load this")).toBeInTheDocument();
    });
  });

  it("renders applications awaiting review with evaluate control", async () => {
    vi.spyOn(http, "get").mockResolvedValueOnce({
      data: {
        results: [
          {
            id: 5,
            application_number: "PMS-2026-005",
            title: "Advanced Heat Exchanger",
            status: "UNDER_REVIEW",
            domain_category: "Mechanical Engineering",
          },
        ],
        next: null,
        previous: null,
      },
    });

    renderWithClient(<ReviewsPage />);
    await waitFor(() => {
      expect(screen.getByText("Advanced Heat Exchanger")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Evaluate Advanced Heat Exchanger" })).toBeInTheDocument();
  });
});
