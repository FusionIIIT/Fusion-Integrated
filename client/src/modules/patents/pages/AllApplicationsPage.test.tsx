import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import AllApplicationsPage from "./AllApplicationsPage";

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

describe("AllApplicationsPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders loading state", () => {
    useAuth.mockReturnValue({ can: () => true });
    vi.spyOn(http, "get").mockReturnValue(new Promise(() => {}));
    renderWithClient(<AllApplicationsPage />);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("renders empty state", async () => {
    useAuth.mockReturnValue({ can: () => true });
    vi.spyOn(http, "get").mockResolvedValueOnce({
      data: { results: [], next: null, previous: null },
    });
    renderWithClient(<AllApplicationsPage />);
    await waitFor(() => {
      expect(screen.getByText("No applications found")).toBeInTheDocument();
    });
  });

  it("renders assign controls when user holds permissions", async () => {
    useAuth.mockReturnValue({
      can: (p: string) => p === "patents.application.assign_director" || p === "patents.attorney.assign",
    });
    vi.spyOn(http, "get").mockResolvedValueOnce({
      data: {
        results: [
          {
            id: 25,
            application_number: "PMS-2026-025",
            title: "Composite Aerogel",
            domain_category: "Material Sciences",
            status: "SUBMITTED",
          },
        ],
        next: null,
        previous: null,
      },
    });

    renderWithClient(<AllApplicationsPage />);
    await waitFor(() => {
      expect(screen.getByText("Composite Aerogel")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: "Assign director to Composite Aerogel" })).toBeInTheDocument();
  });

  it("hides assign controls when user lacks permissions", async () => {
    useAuth.mockReturnValue({ can: () => false });
    vi.spyOn(http, "get").mockResolvedValueOnce({
      data: {
        results: [
          {
            id: 25,
            application_number: "PMS-2026-025",
            title: "Composite Aerogel",
            domain_category: "Material Sciences",
            status: "SUBMITTED",
          },
        ],
        next: null,
        previous: null,
      },
    });

    renderWithClient(<AllApplicationsPage />);
    await waitFor(() => {
      expect(screen.getByText("Composite Aerogel")).toBeInTheDocument();
    });
    expect(screen.queryByRole("button", { name: "Assign director to Composite Aerogel" })).toBeNull();
  });
});
