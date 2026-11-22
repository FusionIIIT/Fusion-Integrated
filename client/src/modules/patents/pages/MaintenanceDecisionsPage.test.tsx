import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import MaintenanceDecisionsPage from "./MaintenanceDecisionsPage";

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

describe("MaintenanceDecisionsPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders loading state", () => {
    vi.spyOn(http, "get").mockReturnValue(new Promise(() => {}));
    renderWithClient(<MaintenanceDecisionsPage />);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("renders empty state", async () => {
    vi.spyOn(http, "get").mockResolvedValueOnce({
      data: { results: [], next: null, previous: null },
    });
    renderWithClient(<MaintenanceDecisionsPage />);
    await waitFor(() => {
      expect(screen.getByText("No maintenance renewals due")).toBeInTheDocument();
    });
  });

  it("renders renewal actions for granted patents", async () => {
    vi.spyOn(http, "get").mockResolvedValueOnce({
      data: {
        results: [
          {
            id: 12,
            application_number: "PMS-2024-001",
            title: "Superconducting Magnet",
            status: "GRANTED",
          },
        ],
        next: null,
        previous: null,
      },
    });

    renderWithClient(<MaintenanceDecisionsPage />);
    await waitFor(() => {
      expect(screen.getByText("Superconducting Magnet")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Renew patent Superconducting Magnet" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Abandon patent Superconducting Magnet" })).toBeInTheDocument();
  });
});
