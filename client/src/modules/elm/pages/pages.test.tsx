import { MantineProvider } from "@mantine/core";
import { fireEvent, render as rtlRender, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const hooks = vi.hoisted(() => ({
  useLeaveCatalog: vi.fn(),
  useLeaveBalances: vi.fn(),
  useMyLeaveRequests: vi.fn(),
  useApplyLeave: vi.fn(),
  useWithdrawLeave: vi.fn(),
  useCancelLeave: vi.fn(),
  useSubstituteTasks: vi.fn(),
  useReviewTasks: vi.fn(),
  useRespondSubstitute: vi.fn(),
  useReviewDecision: vi.fn(),
}));

vi.mock("../api/hooks", () => hooks);

import LeavePage from "./LeavePage";
import LeaveTasksPage from "./LeaveTasksPage";

function render(ui: React.ReactNode) {
  return rtlRender(<MantineProvider>{ui}</MantineProvider>);
}

const baseRequest = {
  id: 1,
  user_id: 101,
  category: "CL",
  start_date: "2026-11-02",
  end_date: "2026-11-02",
  leave_days: "1.00",
  status: "under_review",
  purpose: "Personal",
};

function mutation() {
  return { mutate: vi.fn(), isError: false, isSuccess: false, isPending: false };
}

describe("LeavePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    hooks.useLeaveCatalog.mockReturnValue({ isLoading: false, data: { entitlements: { CL: "8", EL: "30" } } });
    hooks.useLeaveBalances.mockReturnValue({ isLoading: false, data: [{ category: "CL", balance: "8", credited: "8", availed: "0" }] });
    hooks.useMyLeaveRequests.mockReturnValue({ data: [baseRequest] });
    hooks.useApplyLeave.mockReturnValue(mutation());
    hooks.useWithdrawLeave.mockReturnValue(mutation());
    hooks.useCancelLeave.mockReturnValue(mutation());
  });

  it("shows loading until catalog and balances are available", () => {
    hooks.useLeaveCatalog.mockReturnValue({ isLoading: true });
    render(<LeavePage />);
    expect(screen.queryByText("Apply for Leave")).not.toBeInTheDocument();
  });

  it("submits the selected leave fields and omits blank optional ids", () => {
    const apply = mutation();
    hooks.useApplyLeave.mockReturnValue(apply);
    const { container } = render(<LeavePage />);
    const dateInputs = container.querySelectorAll('input[type="date"]');
    fireEvent.change(dateInputs[0]!, { target: { value: "2026-11-10" } });
    fireEvent.change(dateInputs[1]!, { target: { value: "2026-11-11" } });
    fireEvent.change(container.querySelector("textarea")!, { target: { value: "Conference" } });
    fireEvent.click(screen.getByRole("button", { name: "Submit Application" }));
    expect(apply.mutate).toHaveBeenCalledWith(expect.objectContaining({
      category: "CL", start_date: "2026-11-10", end_date: "2026-11-11", purpose: "Conference",
      is_station_leave: false, substitute_id: undefined,
    }));
  });

  it("reveals and requires station details when station leave is selected", () => {
    render(<LeavePage />);
    expect(screen.queryByLabelText("Destination")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("checkbox", { name: "Station Leave Required" }));
    expect(screen.getByRole("textbox", { name: "Destination" })).toBeRequired();
    expect(screen.getByRole("textbox", { name: "Emergency Contact" })).toBeRequired();
  });

  it("offers withdraw for pending requests and cancel for sanctioned requests", () => {
    const pending = { ...baseRequest, status: "awaiting_substitute" };
    const sanctioned = { ...baseRequest, id: 2, status: "sanctioned" };
    hooks.useMyLeaveRequests.mockReturnValue({ data: [pending, sanctioned] });
    const withdraw = mutation();
    const cancel = mutation();
    hooks.useWithdrawLeave.mockReturnValue(withdraw);
    hooks.useCancelLeave.mockReturnValue(cancel);
    render(<LeavePage />);

    const actions = screen.getAllByRole("button", { name: /withdraw|cancel/i });
    expect(actions).toHaveLength(2);
    fireEvent.click(screen.getByRole("button", { name: "Withdraw" }));
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
    expect(withdraw.mutate).toHaveBeenCalledWith(1);
    expect(cancel.mutate).toHaveBeenCalledWith(2);
  });

  it("does not offer lifecycle actions for terminal statuses", () => {
    hooks.useMyLeaveRequests.mockReturnValue({ data: [
      { ...baseRequest, status: "rejected" },
      { ...baseRequest, id: 2, status: "withdrawn" },
      { ...baseRequest, id: 3, status: "cancelled" },
    ] });
    render(<LeavePage />);
    expect(screen.queryByRole("button", { name: "Withdraw" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Cancel" })).not.toBeInTheDocument();
  });
});

describe("LeaveTasksPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    hooks.useSubstituteTasks.mockReturnValue({ isLoading: false, data: [{ ...baseRequest, status: "awaiting_substitute" }] });
    hooks.useReviewTasks.mockReturnValue({ isLoading: false, data: [
      { ...baseRequest, id: 2, category: "CL" },
      { ...baseRequest, id: 3, category: "EL" },
    ] });
    hooks.useRespondSubstitute.mockReturnValue(mutation());
    hooks.useReviewDecision.mockReturnValue(mutation());
  });

  it("shows substitute tasks with accept and decline actions", () => {
    render(<LeaveTasksPage />);
    expect(screen.queryByText("No pending substitute requests.")).not.toBeInTheDocument();
    expect(screen.getByText("Personal")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Accept" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Decline" })).toBeInTheDocument();
  });

  it("sends the chosen substitute action and remarks", () => {
    const respond = mutation();
    hooks.useRespondSubstitute.mockReturnValue(respond);
    render(<LeaveTasksPage />);
    fireEvent.change(screen.getByPlaceholderText("Optional remarks"), { target: { value: "I can cover" } });
    fireEvent.click(screen.getByRole("button", { name: "Accept" }));
    expect(respond.mutate).toHaveBeenCalledWith({ requestId: 1, action: "accept", remarks: "I can cover" });
  });

  it("offers approve for CL and recommend for non-CL/RH leave", () => {
    render(<LeaveTasksPage />);
    fireEvent.click(screen.getByRole("tab", { name: /Pending Approvals/ }));
    expect(screen.getAllByRole("button", { name: "Approve" })).toHaveLength(1);
    expect(screen.getAllByRole("button", { name: "Recommend" })).toHaveLength(1);
    expect(screen.getAllByRole("button", { name: "Reject" })).toHaveLength(2);
  });

  it("submits approve, recommend, and reject decisions with entered reason", () => {
    const review = mutation();
    hooks.useReviewDecision.mockReturnValue(review);
    render(<LeaveTasksPage />);
    fireEvent.click(screen.getByRole("tab", { name: /Pending Approvals/ }));
    const inputs = screen.getAllByPlaceholderText("Review comments");
    fireEvent.change(inputs[0]!, { target: { value: "Approved" } });
    fireEvent.change(inputs[1]!, { target: { value: "Recommend" } });
    fireEvent.click(screen.getAllByRole("button", { name: "Approve" })[0]!);
    fireEvent.click(screen.getAllByRole("button", { name: "Recommend" })[0]!);
    expect(review.mutate).toHaveBeenNthCalledWith(1, { requestId: 2, action: "approve", reason: "Approved" });
    expect(review.mutate).toHaveBeenNthCalledWith(2, { requestId: 3, action: "recommend", reason: "Recommend" });
  });

  it("shows an empty state when there are no tasks", () => {
    hooks.useSubstituteTasks.mockReturnValue({ isLoading: false, data: [] });
    hooks.useReviewTasks.mockReturnValue({ isLoading: false, data: [] });
    render(<LeaveTasksPage />);
    expect(screen.getByText("No pending substitute requests.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: /Pending Approvals/ }));
    expect(screen.getByText("No pending review tasks.")).toBeInTheDocument();
  });
});
