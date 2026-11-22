import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import ReportsPage from "./ReportsPage";

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

describe("ReportsPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders loading state", () => {
    vi.spyOn(http, "get").mockReturnValue(new Promise(() => {}));
    renderWithClient(<ReportsPage />);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("renders error state on failure", async () => {
    vi.spyOn(http, "get").mockRejectedValueOnce(new Error("Service Unavailable"));
    renderWithClient(<ReportsPage />);
    await waitFor(() => {
      expect(screen.getByText("Could not load this")).toBeInTheDocument();
    });
  });

  it("renders metric cards with correct values", async () => {
    vi.spyOn(http, "get").mockResolvedValueOnce({
      data: {
        total_applications: 42,
        filed_count: 28,
        granted_count: 14,
      },
    });

    renderWithClient(<ReportsPage />);
    await waitFor(() => {
      expect(screen.getByText("42")).toBeInTheDocument();
      expect(screen.getByText("28")).toBeInTheDocument();
      expect(screen.getByText("14")).toBeInTheDocument();
    });
    expect(screen.getByText("Total Inventions Disclosed")).toBeInTheDocument();
    expect(screen.getByText("Officially Filed Patents")).toBeInTheDocument();
    expect(screen.getByText("Patents Granted")).toBeInTheDocument();
  });
});
