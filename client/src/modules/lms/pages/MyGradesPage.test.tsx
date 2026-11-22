import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import MyGradesPage from "./MyGradesPage";

const hooks = vi.hoisted(() => ({
  useCourses: vi.fn(),
  useAssignments: vi.fn(),
  useSubmissions: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

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
  title: "Assignment 1",
  instructions: "Do homework",
  points_possible: "100.00",
  submission_type: "FILE",
  due_date: "2026-12-01T23:59:59Z",
  release_date: null,
  status: "PUBLISHED",
  created_by: 1,
  created_at: "2026-11-01",
  updated_at: "2026-11-01",
};

describe("MyGradesPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    hooks.useCourses.mockReturnValue({ data: [sampleCourse], isPending: false });
    hooks.useSubmissions.mockReturnValue({ data: [], isPending: false });
  });

  it("renders loading state while assignments load", () => {
    hooks.useAssignments.mockReturnValue({ data: null, isPending: true, error: null });

    render(
      <MantineProvider>
        <MyGradesPage />
      </MantineProvider>
    );

    expect(screen.getByText(/loading grades/i)).toBeInTheDocument();
  });

  it("renders empty state when there are no assignments", () => {
    hooks.useAssignments.mockReturnValue({ data: [], isPending: false, error: null });

    render(
      <MantineProvider>
        <MyGradesPage />
      </MantineProvider>
    );

    expect(screen.getByText(/no assignments or grades/i)).toBeInTheDocument();
  });

  it("renders error state when fetch fails", () => {
    hooks.useAssignments.mockReturnValue({
      data: null,
      isPending: false,
      error: new Error("Server error"),
    });

    render(
      <MantineProvider>
        <MyGradesPage />
      </MantineProvider>
    );

    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
  });

  it("renders assignment row with max points and not submitted badge", () => {
    hooks.useAssignments.mockReturnValue({
      data: [sampleAssignment],
      isPending: false,
      error: null,
    });
    hooks.useSubmissions.mockReturnValue({ data: [], isPending: false });

    render(
      <MantineProvider>
        <MyGradesPage />
      </MantineProvider>
    );

    expect(screen.getByText("Assignment 1")).toBeInTheDocument();
    expect(screen.getByText(/Max: 100.00 pts/)).toBeInTheDocument();
    expect(screen.getByText(/Not Submitted/)).toBeInTheDocument();
  });
});
