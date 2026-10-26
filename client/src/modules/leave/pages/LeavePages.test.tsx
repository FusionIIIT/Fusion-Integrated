import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { LeaveStatusBadge } from "../components/LeaveStatusBadge";
import CalendarPage from "./CalendarPage";
import PolicyPage from "./PolicyPage";

const useAuth = vi.hoisted(() => vi.fn());
vi.mock("../../../auth/AuthProvider", () => ({ useAuth }));

function renderWithProviders(ui: React.ReactNode) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  useAuth.mockReturnValue({
    can: () => true,
    session: { roles: ["faculty", "HOD", "Leave Administrator"] },
  });

  return render(
    <MantineProvider>
      <QueryClientProvider client={qc}>
        <MemoryRouter
          future={{
            v7_startTransition: true,
            v7_relativeSplatPath: true,
          }}
        >
          {ui}
        </MemoryRouter>
      </QueryClientProvider>
    </MantineProvider>
  );
}

describe("Leave Frontend Pages and Components", () => {
  beforeEach(() => {
    vi.spyOn(http, "get").mockResolvedValue({
      data: [
        {
          code: "CL",
          name: "Casual Leave",
          allows_half_day: true,
          requires_substitute: false,
          is_continuous_count: false,
          carries_forward: false,
        },
        {
          code: "EL",
          name: "Earned Leave",
          allows_half_day: false,
          requires_substitute: true,
          is_continuous_count: true,
          carries_forward: true,
        },
      ],
    });
  });

  it("renders LeaveStatusBadge with uppercase text and light variant", () => {
    render(
      <MantineProvider>
        <LeaveStatusBadge status="awaiting_unit_head" />
      </MantineProvider>
    );
    expect(screen.getByText("AWAITING UNIT HEAD")).toBeInTheDocument();
  });

  it("renders CalendarPage with gazetted and restricted holidays", () => {
    renderWithProviders(<CalendarPage />);
    expect(screen.getByText("Institute Holiday & RH Calendar")).toBeInTheDocument();
    expect(screen.getByText("Gazetted Holidays")).toBeInTheDocument();
    expect(screen.getByText("Restricted Holidays (RH)")).toBeInTheDocument();
    expect(screen.getByText("Republic Day")).toBeInTheDocument();
  });

  it("renders PolicyPage with policy matrix and authority hierarchy", async () => {
    renderWithProviders(<PolicyPage />);
    expect(screen.getByText("Leave Policy & Entitlement Guidelines")).toBeInTheDocument();
    expect(screen.getByText("Casual Leave (CL)")).toBeInTheDocument();
    expect(screen.getByText("Earned Leave (EL)")).toBeInTheDocument();
    expect(screen.getByText("Approval Authority Hierarchy")).toBeInTheDocument();
    expect(screen.getByText("Lifecycle Safeguards & Integrity")).toBeInTheDocument();
  });
});
