import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import OfficeActionsPage from "./OfficeActionsPage";

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

describe("OfficeActionsPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders loading state", () => {
    vi.spyOn(http, "get").mockReturnValue(new Promise(() => {}));
    renderWithClient(<OfficeActionsPage />);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("renders empty state", async () => {
    vi.spyOn(http, "get").mockResolvedValueOnce({
      data: { results: [], next: null, previous: null },
    });
    renderWithClient(<OfficeActionsPage />);
    await waitFor(() => {
      expect(screen.getByText("No pending office actions")).toBeInTheDocument();
    });
  });

  it("renders respond control for pending office actions", async () => {
    vi.spyOn(http, "get").mockResolvedValueOnce({
      data: {
        results: [
          {
            id: 20,
            application_number: "PMS-2025-020",
            title: "Catalytic Converter Coating",
            status: "OFFICE_ACTION_PENDING",
          },
        ],
        next: null,
        previous: null,
      },
    });

    renderWithClient(<OfficeActionsPage />);
    await waitFor(() => {
      expect(screen.getByText("Catalytic Converter Coating")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Respond to action for Catalytic Converter Coating" })).toBeInTheDocument();
  });
});
