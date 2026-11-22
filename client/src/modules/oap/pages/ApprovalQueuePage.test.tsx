import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { StudentLeaveRequest } from "../api/types";
import ApprovalQueuePage from "./ApprovalQueuePage";

const hooks = vi.hoisted(() => ({
  useLeaves: vi.fn(),
  useRecommendLeave: vi.fn(),
  useApproveLeave: vi.fn(),
  useRejectLeave: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const auth = vi.hoisted(() => vi.fn());
vi.mock("../../../auth/AuthProvider", () => ({
  useAuth: auth,
}));

const pendingLeave: StudentLeaveRequest = {
  id: 10,
  student_id: "24BCS205",
  student_name: "Rahul Kumar",
  leave_type: "CASUAL",
  start_date: "2026-12-01",
  end_date: "2026-12-05",
  duration_days: 5,
  reason: "Family function",
  status: "PENDING",
  document_url: "",
  created_at: "2026-11-20T10:00:00Z",
  updated_at: "2026-11-20T10:00:00Z",
};

describe("ApprovalQueuePage", () => {
  beforeEach(() => {
    auth.mockReturnValue({
      can: (p: string) =>
        p === "oap.leave.recommend" || p === "oap.leave.approve",
      session: {
        user: { username: "FACULTY01", display_name: "Prof. Sharma" },
      },
    });
    hooks.useLeaves.mockReturnValue({
      data: { results: [pendingLeave] },
      isPending: false,
      error: null,
    });
    hooks.useRecommendLeave.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue({}),
      isPending: false,
    });
    hooks.useApproveLeave.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue({}),
      isPending: false,
    });
    hooks.useRejectLeave.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue({}),
      isPending: false,
    });
  });

  it("renders pending leave requests for approver", () => {
    render(
      <MantineProvider>
        <ApprovalQueuePage />
      </MantineProvider>,
    );

    expect(screen.getByText("Leave Approval Queue")).toBeInTheDocument();
    expect(screen.getByText("Rahul Kumar")).toBeInTheDocument();
    expect(screen.getByText("24BCS205")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /approve leave/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /recommend leave/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /reject leave/i })).toBeInTheDocument();
  });
});
