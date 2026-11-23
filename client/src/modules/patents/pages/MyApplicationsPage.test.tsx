import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import MyApplicationsPage from "./MyApplicationsPage";

const useAuth = vi.hoisted(() => vi.fn());
vi.mock("../../../auth/AuthProvider", () => ({ useAuth }));

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

describe("MyApplicationsPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders loading state initially", () => {
    useAuth.mockReturnValue({ can: () => true });
    vi.spyOn(http, "get").mockReturnValue(new Promise(() => {}));

    renderWithClient(<MyApplicationsPage />);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("renders empty state when there are no applications", async () => {
    useAuth.mockReturnValue({ can: () => true });
    vi.spyOn(http, "get").mockResolvedValueOnce({
      data: { results: [], next: null, previous: null },
    });

    renderWithClient(<MyApplicationsPage />);
    await waitFor(() => {
      expect(screen.getByText("No applications found")).toBeInTheDocument();
    });
  });

  it("renders error state when API fails with 500", async () => {
    useAuth.mockReturnValue({ can: () => true });
    vi.spyOn(http, "get").mockRejectedValueOnce(new Error("Internal Server Error"));

    renderWithClient(<MyApplicationsPage />);
    await waitFor(() => {
      expect(screen.getByText("Could not load this")).toBeInTheDocument();
    });
  });

  it("renders applications and allows withdraw when user has permission", async () => {
    useAuth.mockReturnValue({
      can: (perm: string) => perm === "patents.application.withdraw" || perm === "patents.application.create",
    });
    vi.spyOn(http, "get").mockResolvedValueOnce({
      data: {
        results: [
          {
            id: 1,
            application_number: "PMS-2026-001",
            title: "Smart Irrigation Robot",
            status: "DRAFT",
            domain_category: "Mechanical Engineering",
            jurisdiction: "IN",
          },
        ],
        next: null,
        previous: null,
      },
    });

    renderWithClient(<MyApplicationsPage />);
    await waitFor(() => {
      expect(screen.getByText("Smart Irrigation Robot")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Withdraw Smart Irrigation Robot" })).toBeInTheDocument();
  });

  it("hides withdraw control when user lacks withdraw permission", async () => {
    useAuth.mockReturnValue({
      can: (perm: string) => perm !== "patents.application.withdraw",
    });
    vi.spyOn(http, "get").mockResolvedValueOnce({
      data: {
        results: [
          {
            id: 1,
            application_number: "PMS-2026-001",
            title: "Smart Irrigation Robot",
            status: "DRAFT",
            domain_category: "Mechanical Engineering",
            jurisdiction: "IN",
          },
        ],
        next: null,
        previous: null,
      },
    });

    renderWithClient(<MyApplicationsPage />);
    await waitFor(() => {
      expect(screen.getByText("Smart Irrigation Robot")).toBeInTheDocument();
    });
    expect(screen.queryByRole("button", { name: "Withdraw Smart Irrigation Robot" })).toBeNull();
  });
});
