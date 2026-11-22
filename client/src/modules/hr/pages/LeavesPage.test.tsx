import { MantineProvider } from "@mantine/core";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import LeavesPage from "./LeavesPage";

const useAuth = vi.hoisted(() => vi.fn());
const useLeaveRequests = vi.hoisted(() => vi.fn());
const useSubmitLeaveRequest = vi.hoisted(() => vi.fn());
const useDecideLeaveRequest = vi.hoisted(() => vi.fn());
vi.mock("../../../auth/AuthProvider", () => ({ useAuth }));
vi.mock("../api/hooks", () => ({
  useLeaveRequests,
  useSubmitLeaveRequest,
  useDecideLeaveRequest,
}));

const makeRequest = (currentAuthority: number | null = null) => ({
  id: 12,
  employee_user_id: 1001,
  leave_type: "casual" as const,
  leave_type_display: "Casual",
  duration_days: "2.00",
  justification: "Family commitment",
  status: "pending_authority" as const,
  current_authority_user_id: currentAuthority,
  authority_step: 0,
  created_at: "2026-11-22T00:00:00Z",
  updated_at: "2026-11-22T00:00:00Z",
  ledger_entries: [],
});

function renderPage() {
  return render(<MantineProvider><LeavesPage /></MantineProvider>);
}

describe("HR leave page", () => {
  beforeEach(() => {
    useAuth.mockReturnValue({ can: (permission: string) => permission === "hr.leave.create",
      session: { user: { id: 1001 } } });
    useLeaveRequests.mockReturnValue({ data: { results: [] }, isPending: false, error: null });
    useSubmitLeaveRequest.mockReturnValue({ mutate: vi.fn(), isPending: false });
    useDecideLeaveRequest.mockReturnValue({ mutate: vi.fn(), isPending: false });
  });

  it("shows loading, empty and request history states", () => {
    useLeaveRequests.mockReturnValueOnce({ data: undefined, isPending: true, error: null });
    const { rerender } = renderPage();
    expect(screen.getByText("Loading leave requests…")).toBeInTheDocument();

    useLeaveRequests.mockReturnValueOnce({ data: { results: [] }, isPending: false, error: null });
    rerender(<MantineProvider><LeavesPage /></MantineProvider>);
    expect(screen.getByText("No leave requests are available.")).toBeInTheDocument();

    useLeaveRequests.mockReturnValueOnce({
      data: { results: [makeRequest()] }, isPending: false, error: null,
    });
    rerender(<MantineProvider><LeavesPage /></MantineProvider>);
    expect(screen.getByText("Family commitment")).toBeInTheDocument();
    expect(screen.getByText("2.00 days")).toBeInTheDocument();
  });

  it("shows a recoverable error state when leave requests fail to load", () => {
    useLeaveRequests.mockReturnValueOnce({
      data: undefined, isPending: false, error: new Error("Request failed"),
    });
    renderPage();
    expect(screen.getByText("Could not load this")).toBeInTheDocument();
    expect(screen.getByText("Something went wrong. Please try again.")).toBeInTheDocument();
  });

  it("submits a selected supported type, duration and justification", async () => {
    const user = userEvent.setup();
    const mutate = vi.fn();
    useSubmitLeaveRequest.mockReturnValue({ mutate, isPending: false });
    renderPage();

    await user.click(screen.getByRole("textbox", { name: "Leave type" }));
    await user.click(screen.getByRole("option", { name: "Casual" }));
    await user.type(screen.getByLabelText("Duration in days"), "2.5");
    await user.type(screen.getByRole("textbox", { name: "Justification" }), "Family commitment");
    await user.click(screen.getByRole("button", { name: "Submit request" }));

    await waitFor(() => expect(mutate).toHaveBeenCalledWith({
      leave_type: "casual", duration_days: "2.5", justification: "Family commitment",
    }, expect.objectContaining({ onSuccess: expect.any(Function), onError: expect.any(Function) })));
  });

  it("offers decisions only to the assigned authority", () => {
    useAuth.mockReturnValue({ can: (permission: string) => permission === "hr.leave.approve",
      session: { user: { id: 88 } } });
    useLeaveRequests.mockReturnValue({
      data: { results: [makeRequest(88)] }, isPending: false, error: null,
    });
    const { rerender } = renderPage();
    expect(screen.getByRole("button", { name: "approve" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "reject" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "forward" })).toBeInTheDocument();

    useLeaveRequests.mockReturnValue({
      data: { results: [makeRequest(99)] }, isPending: false, error: null,
    });
    rerender(<MantineProvider><LeavesPage /></MantineProvider>);
    expect(screen.queryByRole("button", { name: "approve" })).toBeNull();
  });
});
