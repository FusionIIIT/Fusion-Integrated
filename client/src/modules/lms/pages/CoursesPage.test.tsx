import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { chooseCourse, course, mockReads, pageOf, renderLms } from "../test-support";
import type { Submission } from "../api/types";
import CoursesPage from "./CoursesPage";

afterEach(() => vi.restoreAllMocks());
describe("CoursesPage", () => {
  it("shows loading while courses are pending", async () => {
    vi.spyOn(http, "get").mockReturnValue(new Promise(() => undefined));
    renderLms(<CoursesPage />, ["lms.course.view"]);
    expect(await screen.findByRole("status")).toHaveTextContent("Loading course information");
  });
  it("shows an empty course list", async () => {
    mockReads({ "/lms/courses/": { results: [], next: null } });
    renderLms(<CoursesPage />, ["lms.course.view"]);
    expect(await screen.findByText(/No linked courses/)).toBeVisible();
  });
  it("shows a readable API error", async () => {
    vi.spyOn(http, "get").mockRejectedValue({ response: { status: 500, data: { error: { message: "Course service unavailable" } } } });
    renderLms(<CoursesPage />, ["lms.course.view"]);
    expect(await screen.findByRole("alert")).toHaveTextContent("Course service unavailable");
  });
  it("gives observers only common content and no write controls", async () => {
    mockReads({ "/lms/courses/1/": { ...course, acting_course_role: "OBSERVER", can_post_announcements: false } });
    renderLms(<CoursesPage />, ["lms.course.view", "lms.material.view", "lms.announcement.view"]);
    await chooseCourse();
    expect(await screen.findByText("Published syllabus")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Post announcement" })).not.toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Course assignments" })).not.toBeInTheDocument();
    expect(http.get).not.toHaveBeenCalledWith("/lms/courses/1/grades/");
  });
  it("posts an announcement through the shared HTTP client", async () => {
    mockReads();
    vi.spyOn(http, "post").mockResolvedValue({ data: { id: 1 } });
    renderLms(<CoursesPage />, ["lms.course.view", "lms.announcement.create"]);
    await chooseCourse();
    fireEvent.change(await screen.findByLabelText(/Announcement content/), { target: { value: "New lesson" } });
    fireEvent.click(screen.getByRole("button", { name: "Post announcement" }));
    await waitFor(() => expect(http.post).toHaveBeenCalledWith("/lms/courses/1/announcements/", { content: "New lesson" }));
    expect(await screen.findByText("Saved successfully.")).toBeVisible();
  });
  it("shows missing then submitted status for the student's own work", async () => {
    const history = pageOf<Submission>([]);
    const submission: Submission = { id: 3, assignment_id: 2, user_id: 1, kind: "TEXT",
      text: "My work", url: "", file: null, submitted_at: "2026-01-01T00:00:00Z" };
    mockReads({ "/lms/courses/1/": { ...course, acting_course_role: "STUDENT", can_post_announcements: false },
      "/lms/courses/1/assignments/": pageOf([{ id: 2, title: "Exercise", instructions: "Work", state: "AVAILABLE",
        due_at: "2027-01-01", submission_type: "TEXT", points_possible: "20" }]),
      "/lms/assignments/2/submissions/": history });
    vi.spyOn(http, "post").mockImplementation(async () => { history.results = [submission]; return { data: submission }; });
    renderLms(<CoursesPage />, ["lms.course.view", "lms.assignment.view", "lms.submission.view", "lms.submission.create"]);
    await chooseCourse();
    fireEvent.click(await screen.findByRole("button", { name: "View assignment" }));
    expect(await screen.findByText("Submission status: Missing")).toBeVisible();
    fireEvent.change(await screen.findByLabelText(/Submission text/), { target: { value: "My work" } });
    fireEvent.click(screen.getByRole("button", { name: "Submit assignment" }));
    expect(await screen.findByText(/Submission status: Submitted/)).toBeVisible();
    expect(screen.queryByRole("button", { name: "Submit assignment" })).not.toBeInTheDocument();
  });
});
