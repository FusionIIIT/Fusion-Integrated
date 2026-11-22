import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import AttorneyDocketPage from "./AttorneyDocketPage";

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

describe("AttorneyDocketPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders loading state", () => {
    vi.spyOn(http, "get").mockReturnValue(new Promise(() => {}));
    renderWithClient(<AttorneyDocketPage />);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("renders empty state", async () => {
    vi.spyOn(http, "get").mockResolvedValueOnce({
      data: { results: [], next: null, previous: null },
    });
    renderWithClient(<AttorneyDocketPage />);
    await waitFor(() => {
      expect(screen.getByText("Docket is empty")).toBeInTheDocument();
    });
  });

  it("renders assignment action controls", async () => {
    vi.spyOn(http, "get").mockResolvedValueOnce({
      data: {
        results: [
          {
            id: 14,
            application_number: "PMS-2026-014",
            title: "Optical Waveguide",
            status: "ATTORNEY_ASSIGNED",
          },
        ],
        next: null,
        previous: null,
      },
    });

    renderWithClient(<AttorneyDocketPage />);
    await waitFor(() => {
      expect(screen.getByText("Optical Waveguide")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Accept assignment for Optical Waveguide" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Decline assignment for Optical Waveguide" })).toBeInTheDocument();
  });
});
