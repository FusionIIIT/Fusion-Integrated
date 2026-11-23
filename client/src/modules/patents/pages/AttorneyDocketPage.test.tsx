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

  it("renders error state when api fails", async () => {
    vi.spyOn(http, "get").mockRejectedValueOnce(new Error("Database connection failed"));
    renderWithClient(<AttorneyDocketPage />);
    await waitFor(() => {
      expect(screen.getByText(/Could not load this/i)).toBeInTheDocument();
    });
  });

  it("hides accept and decline controls when status is PENDING_REVIEW", async () => {
    vi.spyOn(http, "get").mockResolvedValueOnce({
      data: {
        results: [
          {
            id: 15,
            application_number: "PMS-2026-015",
            title: "Pending Docket App",
            status: "PENDING_REVIEW",
          },
        ],
        next: null,
        previous: null,
      },
    });

    renderWithClient(<AttorneyDocketPage />);
    await waitFor(() => {
      expect(screen.getByText("Pending Docket App")).toBeInTheDocument();
    });
    expect(screen.queryByRole("button", { name: /Accept assignment/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Decline assignment/i })).not.toBeInTheDocument();
  });

  it("executes accept assignment action successfully", async () => {
    vi.spyOn(http, "get").mockResolvedValueOnce({
      data: {
        results: [
          {
            id: 16,
            application_number: "PMS-2026-016",
            title: "Semiconductor Device",
            status: "ATTORNEY_ASSIGNED",
          },
        ],
        next: null,
        previous: null,
      },
    });
    const postSpy = vi.spyOn(http, "post").mockResolvedValueOnce({ data: { status: "ATTORNEY_ASSIGNED" } });

    renderWithClient(<AttorneyDocketPage />);
    await waitFor(() => {
      expect(screen.getByText("Semiconductor Device")).toBeInTheDocument();
    });

    const acceptBtn = screen.getByRole("button", { name: "Accept assignment for Semiconductor Device" });
    acceptBtn.click();
    await waitFor(() => {
      expect(postSpy).toHaveBeenCalledWith("/patents/applications/16/respond-assignment", { action: "accept" });
    });
  });
});
