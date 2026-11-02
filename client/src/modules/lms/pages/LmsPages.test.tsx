import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { CourseCard } from "../components/CourseCard";
import { MaterialItem } from "../components/MaterialItem";
import { AnnouncementItem } from "../components/AnnouncementItem";
import { AssignmentItem } from "../components/AssignmentItem";
import { GradingModal } from "../components/GradingModal";
import { SubmissionModal } from "../components/SubmissionModal";
import type {
  Course,
  CourseMaterial,
  Announcement,
  Assignment,
  Submission,
} from "../api/types";

function renderWithProviders(ui: React.ReactElement) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <MantineProvider>
      <QueryClientProvider client={qc}>
        <MemoryRouter>{ui}</MemoryRouter>
      </QueryClientProvider>
    </MantineProvider>
  );
}

describe("LMS UI Components & Policy Enforcements", () => {
  const mockCourse: Course = {
    id: 1,
    code: "CS301",
    name: "Software Engineering",
    description: "Design and construction of large scale software systems",
    academic_year: 2026,
    semester: 1,
    is_active: true,
    created_at: "2026-08-01T00:00:00Z",
    updated_at: "2026-08-01T00:00:00Z",
  };

  const mockAssignment: Assignment = {
    id: 10,
    course: 1,
    title: "Assignment 1: System Architecture",
    description: "Submit architecture documentation",
    points_possible: 100,
    due_date: "2026-11-15T23:59:59Z",
    submission_type: "file",
    is_published: true,
    created_at: "2026-11-01T00:00:00Z",
    updated_at: "2026-11-01T00:00:00Z",
  };

  const mockSubmission: Submission = {
    id: 101,
    assignment: 10,
    student_user_id: 202,
    version: 1,
    submission_type: "file",
    file_storage_key: "submissions/202_assign1_v1.pdf",
    submitted_at: "2026-11-02T10:00:00Z",
    status: "submitted",
    created_at: "2026-11-02T10:00:00Z",
    updated_at: "2026-11-02T10:00:00Z",
  };

  it("CourseCard renders course code, name, and semester details", () => {
    renderWithProviders(<CourseCard course={mockCourse} />);
    expect(screen.getByText("CS301")).toBeInTheDocument();
    expect(screen.getByText("Software Engineering")).toBeInTheDocument();
    expect(screen.getByText("Academic Year: 2026 • Semester: 1")).toBeInTheDocument();
    expect(screen.getByText("Open Workspace")).toBeInTheDocument();
  });

  it("MaterialItem renders note, file and link types correctly", () => {
    const noteMaterial: CourseMaterial = {
      id: 1,
      course: 1,
      title: "Lecture 1 Notes",
      material_type: "note",
      note_content: "Welcome to Software Engineering",
      is_published: true,
      order: 1,
      created_at: "2026-11-01T00:00:00Z",
      updated_at: "2026-11-01T00:00:00Z",
    };

    renderWithProviders(<MaterialItem material={noteMaterial} />);
    expect(screen.getByText("Lecture 1 Notes")).toBeInTheDocument();
    expect(screen.getByText("NOTE")).toBeInTheDocument();
    expect(screen.getByText("Welcome to Software Engineering")).toBeInTheDocument();
  });

  it("AnnouncementItem renders title, author role and content", () => {
    const announcement: Announcement = {
      id: 1,
      course: 1,
      title: "Midterm Schedule Announced",
      content: "Midterm will take place next Friday.",
      author_user_id: 5,
      author_role: "instructor",
      is_pinned: true,
      created_at: "2026-11-01T00:00:00Z",
      updated_at: "2026-11-01T00:00:00Z",
    };

    renderWithProviders(<AnnouncementItem announcement={announcement} />);
    expect(screen.getByText("Midterm Schedule Announced")).toBeInTheDocument();
    expect(screen.getByText("Pinned")).toBeInTheDocument();
    expect(screen.getByText("Midterm will take place next Friday.")).toBeInTheDocument();
  });

  it("AssignmentItem renders assignment details and points", () => {
    renderWithProviders(<AssignmentItem assignment={mockAssignment} isStudent={true} />);
    expect(screen.getByText("Assignment 1: System Architecture")).toBeInTheDocument();
    expect(screen.getByText("100 pts")).toBeInTheDocument();
    expect(screen.getByText("FILE")).toBeInTheDocument();
  });

  it("GradingModal displays TA policy warning and restricts release action for TA role (BW-LMS-05 / ISS-LMS-002)", () => {
    renderWithProviders(
      <GradingModal
        opened={true}
        onClose={() => {}}
        submission={mockSubmission}
        assignment={mockAssignment}
        userRole="ta"
      />
    );

    // TA policy warning should be visible
    expect(
      screen.getByText(/TA Authorization Policy \(BW-LMS-05 \/ ISS-LMS-002\)/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/As a Teaching Assistant, your assessments are recorded in Draft mode/i)
    ).toBeInTheDocument();

    // "Release Grade" button should be disabled for TA
    const releaseBtn = screen.getByRole("button", { name: /Release Grade/i });
    expect(releaseBtn).toBeDisabled();

    // "Save Draft" should remain enabled for TA
    const draftBtn = screen.getByRole("button", { name: /Save Draft/i });
    expect(draftBtn).not.toBeDisabled();
  });

  it("GradingModal allows release action for Instructor role", () => {
    renderWithProviders(
      <GradingModal
        opened={true}
        onClose={() => {}}
        submission={mockSubmission}
        assignment={mockAssignment}
        userRole="instructor"
      />
    );

    // Release Grade should be enabled for Instructor
    const releaseBtn = screen.getByRole("button", { name: /Release Grade/i });
    expect(releaseBtn).not.toBeDisabled();
  });

  it("SubmissionModal renders submission interface with file upload and policy details", () => {
    renderWithProviders(
      <SubmissionModal
        opened={true}
        onClose={() => {}}
        assignment={mockAssignment}
      />
    );

    expect(
      screen.getByText(/Submit: Assignment 1: System Architecture/i)
    ).toBeInTheDocument();
    expect(screen.getByText(/Select Submission File/i)).toBeInTheDocument();
    expect(screen.getByText(/File Upload/i)).toBeInTheDocument();
  });
});
