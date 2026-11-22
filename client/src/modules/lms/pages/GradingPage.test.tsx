import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import GradingPage from "./GradingPage";

const hooks = vi.hoisted(() => ({
  useCourses: vi.fn(),
  useAssignments: vi.fn(),
  useSubmissions: vi.fn(),
  useGradeSubmission: vi.fn(),
  useUpdateGrade: vi.fn(),
  usePublishGrades: vi.fn(),
  useGradeAudits: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const useAuth = vi.hoisted(() => vi.fn());
vi.mock("../../../auth/AuthProvider", () => ({ useAuth }));

const sampleCourse = {
  id: 1,
  course_id: 101,
  course_code: "CS101",
  title: "Introduction to Computer Science",
  role: "INSTRUCTOR",
};

const sampleAssignment = {
  id: 10,
  course_id: 101,
  title: "Midterm Assignment",
  instructions: "Answer all questions.",
  points_possible: "100.00",
  submission_type: "FILE",
  due_date: "2026-11-20T23:59:59Z",
  release_date: null,
  status: "PUBLISHED",
  created_by: 1,
  created_at: "2026-11-01",
  updated_at: "2026-11-01",
};

const sampleSubmission = {
  id: 101,
  assignment: 10,
  student_id: 42,
  submission_type: "FILE",
  content_text: "",
  content_link: "",
  file_attachment: "/media/lms/sub.pdf",
  submitted_at: "2026-11-19T10:00:00Z",
  attempt_number: 1,
  status: "SUBMITTED",
};

describe("GradingPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    hooks.useCourses.mockReturnValue({ data: [sampleCourse], isPending: false });
    hooks.useAssignments.mockReturnValue({ data: [sampleAssignment], isPending: false });
    hooks.useGradeSubmission.mockReturnValue({ mutate: vi.fn(), isPending: false });
    hooks.useUpdateGrade.mockReturnValue({ mutate: vi.fn(), isPending: false });
    hooks.usePublishGrades.mockReturnValue({ mutate: vi.fn(), isPending: false });
    hooks.useGradeAudits.mockReturnValue({ data: [], isPending: false });
  });

  it("renders loading state while submissions load", () => {
    useAuth.mockReturnValue({ can: () => false });
    hooks.useSubmissions.mockReturnValue({ data: null, isPending: true, error: null });

    render(
      <MantineProvider>
        <GradingPage />
      </MantineProvider>
    );

    expect(screen.getByText(/loading student submissions/i)).toBeInTheDocument();
  });

  it("renders empty state when there are no submissions", () => {
    useAuth.mockReturnValue({ can: () => false });
    hooks.useSubmissions.mockReturnValue({ data: [], isPending: false, error: null });

    render(
      <MantineProvider>
        <GradingPage />
      </MantineProvider>
    );

    expect(screen.getByText(/no submissions found for this assignment/i)).toBeInTheDocument();
  });

  it("renders error state on fetch failure", () => {
    useAuth.mockReturnValue({ can: () => false });
    hooks.useSubmissions.mockReturnValue({
      data: null,
      isPending: false,
      error: new Error("Failed to load submissions"),
    });

    render(
      <MantineProvider>
        <GradingPage />
      </MantineProvider>
    );

    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
  });

  it("renders submissions table and Grade button", () => {
    useAuth.mockReturnValue({ can: () => false });
    hooks.useSubmissions.mockReturnValue({
      data: [sampleSubmission],
      isPending: false,
      error: null,
    });

    render(
      <MantineProvider>
        <GradingPage />
      </MantineProvider>
    );

    expect(screen.getByText(/User 42/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^grade$/i })).toBeInTheDocument();
  });

  it("shows Publish Draft Grades button when user holds lms.grade.publish (Faculty)", () => {
    useAuth.mockReturnValue({ can: (p: string) => p === "lms.grade.publish" });
    hooks.useSubmissions.mockReturnValue({
      data: [sampleSubmission],
      isPending: false,
      error: null,
    });

    render(
      <MantineProvider>
        <GradingPage />
      </MantineProvider>
    );

    expect(screen.getByRole("button", { name: /publish draft grades/i })).toBeInTheDocument();
  });

  it("hides Publish Draft Grades button when user lacks lms.grade.publish (TA)", () => {
    useAuth.mockReturnValue({ can: () => false });
    hooks.useSubmissions.mockReturnValue({
      data: [sampleSubmission],
      isPending: false,
      error: null,
    });

    render(
      <MantineProvider>
        <GradingPage />
      </MantineProvider>
    );

    expect(screen.queryByRole("button", { name: /publish draft grades/i })).toBeNull();
  });
});
