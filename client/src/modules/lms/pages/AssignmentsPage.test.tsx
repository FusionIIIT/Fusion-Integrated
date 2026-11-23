import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AssignmentsPage from "./AssignmentsPage";

const hooks = vi.hoisted(() => ({
  useCourses: vi.fn(),
  useAssignments: vi.fn(),
  useCreateAssignment: vi.fn(),
  usePublishAssignment: vi.fn(),
  useSubmitAssignment: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const useAuth = vi.hoisted(() => vi.fn());
vi.mock("../../../auth/AuthProvider", () => ({ useAuth }));

const sampleCourse = {
  id: 1,
  course_id: 101,
  course_code: "CS101",
  title: "Introduction to Computer Science",
  role: "STUDENT",
};

const sampleAssignment = {
  id: 1,
  course_id: 101,
  title: "Assignment 1: Sorting Algorithms",
  instructions: "Implement merge sort and quick sort.",
  points_possible: "100.00",
  submission_type: "FILE",
  due_date: "2026-12-01T23:59:59Z",
  release_date: null,
  status: "PUBLISHED",
  created_by: 1,
  created_at: "2026-11-01",
  updated_at: "2026-11-01",
};

const draftAssignment = {
  ...sampleAssignment,
  id: 2,
  title: "Draft Assignment 2",
  status: "DRAFT",
};

describe("AssignmentsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    hooks.useCourses.mockReturnValue({ data: [sampleCourse], isPending: false });
    hooks.useCreateAssignment.mockReturnValue({ mutate: vi.fn(), isPending: false });
    hooks.usePublishAssignment.mockReturnValue({ mutate: vi.fn(), isPending: false });
    hooks.useSubmitAssignment.mockReturnValue({ mutate: vi.fn(), isPending: false });
  });

  it("renders loading state while assignments load", () => {
    useAuth.mockReturnValue({ can: () => false });
    hooks.useAssignments.mockReturnValue({ data: null, isPending: true, error: null });

    render(
      <MantineProvider>
        <AssignmentsPage />
      </MantineProvider>
    );

    expect(screen.getByText(/loading assignments/i)).toBeInTheDocument();
  });

  it("renders empty state when there are no assignments", () => {
    useAuth.mockReturnValue({ can: () => false });
    hooks.useAssignments.mockReturnValue({ data: [], isPending: false, error: null });

    render(
      <MantineProvider>
        <AssignmentsPage />
      </MantineProvider>
    );

    expect(screen.getByText(/no assignments posted/i)).toBeInTheDocument();
  });

  it("renders error state when fetch fails", () => {
    useAuth.mockReturnValue({ can: () => false });
    hooks.useAssignments.mockReturnValue({
      data: null,
      isPending: false,
      error: new Error("Error loading"),
    });

    render(
      <MantineProvider>
        <AssignmentsPage />
      </MantineProvider>
    );

    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
  });

  it("shows Create Assignment button when user has lms.assignment.create", () => {
    useAuth.mockReturnValue({ can: (p: string) => p === "lms.assignment.create" });
    hooks.useAssignments.mockReturnValue({
      data: [sampleAssignment],
      isPending: false,
      error: null,
    });

    render(
      <MantineProvider>
        <AssignmentsPage />
      </MantineProvider>
    );

    expect(screen.getByText("Assignment 1: Sorting Algorithms")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /create assignment/i })).toBeInTheDocument();
  });

  it("shows Submit button when user has lms.submission.create", () => {
    useAuth.mockReturnValue({ can: (p: string) => p === "lms.submission.create" });
    hooks.useAssignments.mockReturnValue({
      data: [sampleAssignment],
      isPending: false,
      error: null,
    });

    render(
      <MantineProvider>
        <AssignmentsPage />
      </MantineProvider>
    );

    expect(screen.getByRole("button", { name: /submit/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /create assignment/i })).toBeNull();
  });

  it("shows Publish button for draft assignment when user has lms.assignment.publish", () => {
    useAuth.mockReturnValue({ can: (p: string) => p === "lms.assignment.publish" });
    hooks.useAssignments.mockReturnValue({
      data: [draftAssignment],
      isPending: false,
      error: null,
    });

    render(
      <MantineProvider>
        <AssignmentsPage />
      </MantineProvider>
    );

    expect(screen.getByText("Draft Assignment 2")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /publish/i })).toBeInTheDocument();
  });
});
