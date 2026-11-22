import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import CourseWorkspacePage from "./CourseWorkspacePage";

const hooks = vi.hoisted(() => ({
  useCourseDetail: vi.fn(),
  useCourseMaterials: vi.fn(),
  useCourseAnnouncements: vi.fn(),
  useCourseAssignments: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

describe("CourseWorkspacePage", () => {
  beforeEach(() => {
    hooks.useCourseDetail.mockReturnValue({
      data: {
        id: 1,
        course_code: "CS101",
        title: "Intro to CS",
        syllabus: "CS101 Syllabus",
        schedule: "MWF 10am",
        user_role: "student",
      },
      isLoading: false,
      error: null,
    });
    hooks.useCourseMaterials.mockReturnValue({ data: [] });
    hooks.useCourseAnnouncements.mockReturnValue({ data: [] });
    hooks.useCourseAssignments.mockReturnValue({ data: [] });
  });

  it("renders course workspace page correctly", () => {
    render(
      <MantineProvider>
        <BrowserRouter>
          <CourseWorkspacePage />
        </BrowserRouter>
      </MantineProvider>
    );

    expect(screen.getByText("CS101: Intro to CS")).toBeInTheDocument();
  });
});
