import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import CourseListPage from "./CourseListPage";

const hooks = vi.hoisted(() => ({
  useUserCourses: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

describe("CourseListPage", () => {
  beforeEach(() => {
    hooks.useUserCourses.mockReturnValue({
      data: [
        {
          id: 1,
          course: 10,
          course_code: "CS101",
          course_title: "Intro to CS",
          role: "student",
          can_post_announcements: false,
        },
      ],
      isLoading: false,
      error: null,
    });
  });

  it("renders enrolled courses correctly", () => {
    render(
      <MantineProvider>
        <BrowserRouter>
          <CourseListPage />
        </BrowserRouter>
      </MantineProvider>
    );

    expect(screen.getByText("Course Management (LMS)")).toBeInTheDocument();
    expect(screen.getByText("CS101")).toBeInTheDocument();
    expect(screen.getByText("Intro to CS")).toBeInTheDocument();
    expect(screen.getByText("Open Workspace")).toBeInTheDocument();
  });
});
