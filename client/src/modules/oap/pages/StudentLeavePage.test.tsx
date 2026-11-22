import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { StudentLeaveRequest } from "../api/types";
import StudentLeavePage from "./StudentLeavePage";

const hooks = vi.hoisted(() => ({
  useLeaves: vi.fn(),
  useSubmitLeave: vi.fn(),
  useCancelLeave: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const auth = vi.hoisted(() => vi.fn());
vi.mock("../../../auth/AuthProvider", () => ({
  useAuth: auth,
}));

const sampleLeave: StudentLeaveRequest = {
  id: 1,
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

describe("StudentLeavePage", () => {
  beforeEach(() => {
    auth.mockReturnValue({
      can: (p: string) => p === "oap.leave.create",
      session: {
        user: { username: "24BCS205", display_name: "Rahul Kumar" },
      },
    });
    hooks.useLeaves.mockReturnValue({
      data: { results: [sampleLeave] },
      isPending: false,
      error: null,
    });
    hooks.useSubmitLeave.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue({ id: 2 }),
      isPending: false,
    });
    hooks.useCancelLeave.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue({}),
      isPending: false,
    });
  });

  it("renders loading state", () => {
    hooks.useLeaves.mockReturnValue({
      data: null,
      isPending: true,
      error: null,
    });

    render(
      <MantineProvider>
        <StudentLeavePage />
      </MantineProvider>,
    );

    expect(screen.getByText(/loading leave applications/i)).toBeInTheDocument();
  });

  it("renders error state", () => {
    hooks.useLeaves.mockReturnValue({
      data: null,
      isPending: false,
      error: new Error("Server communication failure"),
    });

    render(
      <MantineProvider>
        <StudentLeavePage />
      </MantineProvider>,
    );

    expect(screen.getByText(/could not load this/i)).toBeInTheDocument();
  });

  it("renders leaves list and details", () => {
    render(
      <MantineProvider>
        <StudentLeavePage />
      </MantineProvider>,
    );

    expect(screen.getByText("Student Leave Applications")).toBeInTheDocument();
    expect(screen.getByText("Family function")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /apply for leave/i })).toBeInTheDocument();
  });
});
