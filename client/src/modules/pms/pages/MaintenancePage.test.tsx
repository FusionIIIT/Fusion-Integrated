import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { application } from "./pageTestFixtures";
import MaintenancePage from "./MaintenancePage";

const hooks = vi.hoisted(() => ({
  usePmsApplication: vi.fn(),
  usePmsAction: vi.fn(() => ({ mutate: vi.fn(), isPending: false, error: null })),
}));
const auth = vi.hoisted(() => ({ can: vi.fn() }));
vi.mock("../api/hooks", () => hooks);
vi.mock("../../../auth/AuthProvider", () => ({ useAuth: () => auth }));
vi.mock("../components/PmsApplicationSelect", () => ({
  PmsApplicationSelect: ({ onChange }: { onChange: (id: string) => void }) => (
    <button onClick={() => onChange("41")}>Select application</button>
  ),
}));

describe("MaintenancePage (UC-PMS-020, UC-PMS-021)", () => {
  beforeEach(() => {
    auth.can.mockReturnValue(false);
    hooks.usePmsApplication.mockReturnValue({ data: application, isPending: false, error: null });
  });

  it("documents the no-cycle empty state and hides renewal controls without permission", () => {
    render(<MantineProvider><MaintenancePage /></MantineProvider>);
    fireEvent.click(screen.getByRole("button", { name: "Select application" }));
    expect(screen.getByText(/No maintenance cycle is recorded/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Request Director decision" })).not.toBeInTheDocument();
  });

  it("shows a renewal action when the configured cycle and permission allow it", () => {
    auth.can.mockImplementation((permission: string) => permission === "pms.maintenance.manage");
    hooks.usePmsApplication.mockReturnValue({
      data: { ...application, maintenance_records: [{
        id: 9, cycle_number: 1, fee_due_date: "2027-01-01", fee_amount: "100",
        decision_requested: false, director_decision: "", renewal_decided_at: null,
        maintenance_status: "scheduled", action_recorded_date: null, transaction_reference: "",
      }] }, isPending: false, error: null,
    });
    render(<MantineProvider><MaintenancePage /></MantineProvider>);
    fireEvent.click(screen.getByRole("button", { name: "Select application" }));
    expect(screen.getByRole("button", { name: "Request Director decision" })).toBeInTheDocument();
  });

  it("shows detail loading and error states", () => {
    hooks.usePmsApplication.mockReturnValue({ data: undefined, isPending: true, error: null });
    const { rerender } = render(<MantineProvider><MaintenancePage /></MantineProvider>);
    fireEvent.click(screen.getByRole("button", { name: "Select application" }));
    expect(screen.getByText("Loading application…")).toBeInTheDocument();
    hooks.usePmsApplication.mockReturnValue({
      data: undefined, isPending: false,
      error: { response: { data: { error: { message: "Maintenance service unavailable" } } } },
    });
    rerender(<MantineProvider><MaintenancePage /></MantineProvider>);
    expect(screen.getByText("Maintenance service unavailable")).toBeInTheDocument();
  });
});
