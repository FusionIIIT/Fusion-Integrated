import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import CoursesPage from "./CoursesPage";

const hooks = vi.hoisted(() => ({
  useCourses: vi.fn(),
  useCourseDetail: vi.fn(),
  useUpdateCourse: vi.fn(),
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

const sampleDetail = {
  id: 1,
  course_id: 101,
  course_code: "CS101",
  title: "Introduction to Computer Science",
  syllabus: "Algorithms and Data Structures",
  schedule_info: "Mon/Wed 10:00 AM",
  instructors: [1],
  teaching_assistants: [2],
};

describe("CoursesPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    hooks.useUpdateCourse.mockReturnValue({ mutate: vi.fn(), isPending: false });
  });

  it("renders loading state while fetching courses", () => {
    useAuth.mockReturnValue({ can: () => false });
    hooks.useCourses.mockReturnValue({ data: null, isPending: true, error: null });
    hooks.useCourseDetail.mockReturnValue({ data: null, isPending: false });

    render(
      <MantineProvider>
        <CoursesPage />
      </MantineProvider>
    );

    expect(screen.getByText(/loading your enrolled courses/i)).toBeInTheDocument();
  });

  it("renders empty state when user has no active course enrollments", () => {
    useAuth.mockReturnValue({ can: () => false });
    hooks.useCourses.mockReturnValue({ data: [], isPending: false, error: null });
    hooks.useCourseDetail.mockReturnValue({ data: null, isPending: false });

    render(
      <MantineProvider>
        <CoursesPage />
      </MantineProvider>
    );

    expect(screen.getByText(/no active course enrollments found/i)).toBeInTheDocument();
  });

  it("renders error state when fetch fails", () => {
    useAuth.mockReturnValue({ can: () => false });
    hooks.useCourses.mockReturnValue({
      data: null,
      isPending: false,
      error: new Error("Network error"),
    });
    hooks.useCourseDetail.mockReturnValue({ data: null, isPending: false });

    render(
      <MantineProvider>
        <CoursesPage />
      </MantineProvider>
    );

    expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
  });

  it("renders course details and shows edit button when user holds lms.workspace.update", () => {
    useAuth.mockReturnValue({ can: (p: string) => p === "lms.workspace.update" });
    hooks.useCourses.mockReturnValue({ data: [sampleCourse], isPending: false, error: null });
    hooks.useCourseDetail.mockReturnValue({ data: sampleDetail, isPending: false });

    render(
      <MantineProvider>
        <CoursesPage />
      </MantineProvider>
    );

    expect(screen.getByText("CS101: Introduction to Computer Science")).toBeInTheDocument();
    expect(screen.getByText("Algorithms and Data Structures")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /edit course details/i })).toBeInTheDocument();
  });

  it("hides edit button when user lacks lms.workspace.update", () => {
    useAuth.mockReturnValue({ can: () => false });
    hooks.useCourses.mockReturnValue({ data: [sampleCourse], isPending: false, error: null });
    hooks.useCourseDetail.mockReturnValue({ data: sampleDetail, isPending: false });

    render(
      <MantineProvider>
        <CoursesPage />
      </MantineProvider>
    );

    expect(screen.getByText("CS101: Introduction to Computer Science")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /edit course details/i })).toBeNull();
  });
});
