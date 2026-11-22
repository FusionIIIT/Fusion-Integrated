import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import AttorneyPanelPage from "./AttorneyPanelPage";

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

describe("AttorneyPanelPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders loading state", () => {
    vi.spyOn(http, "get").mockReturnValue(new Promise(() => {}));
    renderWithClient(<AttorneyPanelPage />);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("renders empty state", async () => {
    vi.spyOn(http, "get").mockResolvedValueOnce({
      data: { results: [], next: null, previous: null },
    });
    renderWithClient(<AttorneyPanelPage />);
    await waitFor(() => {
      expect(screen.getByText("No panel attorneys enrolled")).toBeInTheDocument();
    });
  });

  it("renders attorney panel member table", async () => {
    vi.spyOn(http, "get").mockResolvedValueOnce({
      data: {
        results: [
          {
            id: 1,
            user_id: 30,
            firm_name: "Metis IP Associates",
            active_workload: 3,
            is_approved_panel: true,
          },
        ],
        next: null,
        previous: null,
      },
    });

    renderWithClient(<AttorneyPanelPage />);
    await waitFor(() => {
      expect(screen.getByText("Metis IP Associates")).toBeInTheDocument();
    });
    expect(screen.getByText("Approved Panel")).toBeInTheDocument();
  });
});
