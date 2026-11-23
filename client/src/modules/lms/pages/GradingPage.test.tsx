import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { chooseCourse, course, facultyPermissions, mockReads, pageOf, renderLms } from "../test-support";
import GradingPage from "./GradingPage";

afterEach(() => vi.restoreAllMocks());
describe("GradingPage", () => {
  it("shows loading", async () => {
    vi.spyOn(http, "get").mockReturnValue(new Promise(() => undefined));
    renderLms(<GradingPage />, facultyPermissions);
    expect(await screen.findByRole("status")).toBeVisible();
  });
  it("shows no linked courses", async () => {
    mockReads({ "/lms/courses/": pageOf([]) });
    renderLms(<GradingPage />, facultyPermissions);
    expect(await screen.findByText(/No linked courses/)).toBeVisible();
  });
  it("shows the server error", async () => {
    vi.spyOn(http, "get").mockRejectedValue({ response: { status: 500, data: { error: { message: "Grading unavailable" } } } });
    renderLms(<GradingPage />, facultyPermissions);
    expect(await screen.findByRole("alert")).toHaveTextContent("Grading unavailable");
  });
  it("does not fetch when the route is forbidden", async () => {
    mockReads();
    renderLms(<GradingPage />, ["lms.course.view"], "lms.grade.update");
    expect(await screen.findByText(/Not available to your role/i)).toBeVisible();
    expect(http.get).not.toHaveBeenCalled();
  });
  it("saves a draft grade and displays the server refusal", async () => {
    mockReads({ "/lms/courses/1/assignments/": pageOf([{ id: 2, title: "Exercise" }]),
      "/lms/assignments/2/submissions/": pageOf([{ id: 3, assignment_id: 2, user_id: 4, kind: "TEXT", text: "Work", submitted_at: "2026-01-01", file: null }]) });
    vi.spyOn(http, "post").mockRejectedValue({ response: { status: 422, data: { error: { message: "Points must be nonnegative" } } } });
    renderLms(<GradingPage />, facultyPermissions);
    await chooseCourse();
    fireEvent.change(await screen.findByLabelText("Assignment to grade"), { target: { value: "2" } });
    fireEvent.change(await screen.findByLabelText(/Points for submission 3/), { target: { value: "12" } });
    fireEvent.change(screen.getByLabelText("Feedback for submission 3"), { target: { value: "Reviewed" } });
    fireEvent.click(screen.getByRole("button", { name: "Save draft grade" }));
    await waitFor(() => expect(http.post).toHaveBeenCalledWith("/lms/submissions/3/grade/", { points: "12", feedback: "Reviewed" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Points must be nonnegative");
  });

  it("shows a selected course detail error instead of a spinner", async () => {
    mockReads({}, { "/lms/courses/1/": { response: { status: 503, data: { error: { message: "Course detail unavailable" } } } } });
    renderLms(<GradingPage />, facultyPermissions);
    await chooseCourse();
    expect(await screen.findByRole("alert")).toHaveTextContent("Course detail unavailable");
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it.each(["create", "update"])("hides a mounted grading form without grade.%s", async (action) => {
    const row = { id: 3, assignment_id: 2, user_id: 4, kind: "TEXT", text: "Work", submitted_at: "2026-01-01", file: null };
    mockReads({
      "/lms/courses/1/assignments/": pageOf([{ id: 2, title: "Exercise" }]),
      "/lms/assignments/2/submissions/": pageOf([row]),
      "/lms/courses/1/grades/": pageOf(action === "update" ? [{ id: 8, submission_id: 3, state: "DRAFT", points: "10", feedback: "Draft" }] : []),
    });
    renderLms(<GradingPage />, facultyPermissions.filter((permission) => permission !== `lms.grade.${action}`));
    await chooseCourse();
    fireEvent.change(await screen.findByLabelText("Assignment to grade"), { target: { value: "2" } });
    expect(await screen.findByRole("heading", { name: /Submission 3/ })).toBeVisible();
    expect(screen.queryByRole("button", { name: "Save draft grade" })).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Points for submission 3")).not.toBeInTheDocument();
  });

  it("does not infer an ungraded submission while later grade pages are unknown", async () => {
    const taPermissions = ["lms.course.view", "lms.assignment.view", "lms.submission.view", "lms.grade.view", "lms.grade.create", "lms.grade.update"];
    mockReads({
      "/lms/courses/1/": { ...course, acting_course_role: "TA" },
      "/lms/courses/1/assignments/": pageOf([{ id: 2, title: "Older exercise" }]),
      "/lms/assignments/2/submissions/": pageOf([{ id: 3, assignment_id: 2, user_id: 4, kind: "TEXT", text: "Work", submitted_at: "2026-01-01", file: null }]),
      "/lms/courses/1/grades/": { ...pageOf(Array.from({ length: 25 }, (_, index) => ({ id: 100 + index, submission_id: 100 + index, state: "DRAFT", points: "10", feedback: "Other" }))), next: "http://testserver/api/v1/lms/courses/1/grades/?cursor=later" },
      "/lms/courses/1/grades/?cursor=later": pageOf([{ id: 8, submission_id: 3, state: "RELEASED", points: "15", feedback: "Released feedback" }]),
    });
    renderLms(<GradingPage />, taPermissions, undefined, "lms_ta");
    await chooseCourse();
    fireEvent.change(await screen.findByLabelText("Assignment to grade"), { target: { value: "2" } });
    expect(await screen.findByText(/Load more grades to determine/)).toBeVisible();
    expect(screen.queryByRole("button", { name: "Save draft grade" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Load more grades" }));
    expect(await screen.findByText("Grade RELEASED: 15 · Released feedback")).toBeVisible();
    expect(screen.queryByRole("button", { name: "Save draft grade" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Correct released grade" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Release grade/ })).not.toBeInTheDocument();
  });

  it("shows an authoritative ungraded form only after all grade pages are loaded", async () => {
    mockReads({
      "/lms/courses/1/assignments/": pageOf([{ id: 2, title: "Exercise" }]),
      "/lms/assignments/2/submissions/": pageOf([{ id: 3, assignment_id: 2, user_id: 4, kind: "TEXT", text: "Work", submitted_at: "2026-01-01", file: null }]),
      "/lms/courses/1/grades/": { ...pageOf([]), next: "http://testserver/api/v1/lms/courses/1/grades/?cursor=later" },
      "/lms/courses/1/grades/?cursor=later": pageOf([]),
    });
    renderLms(<GradingPage />, facultyPermissions);
    await chooseCourse();
    fireEvent.change(await screen.findByLabelText("Assignment to grade"), { target: { value: "2" } });
    expect(await screen.findByText(/Load more grades to determine/)).toBeVisible();
    expect(screen.queryByRole("button", { name: "Save draft grade" })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Load more grades" }));
    expect(await screen.findByRole("button", { name: "Save draft grade" })).toBeVisible();
  });

  it("keeps grading and release controls hidden for the submission owner", async () => {
    mockReads({
      "/lms/courses/1/assignments/": pageOf([{ id: 2, title: "Exercise" }]),
      "/lms/assignments/2/submissions/": pageOf([{ id: 3, assignment_id: 2, user_id: 1, kind: "TEXT", text: "My work", submitted_at: "2026-01-01", file: null }]),
      "/lms/courses/1/grades/": pageOf([{ id: 8, submission_id: 3, state: "DRAFT", points: "10", feedback: "Draft" }]),
    });
    renderLms(<GradingPage />, facultyPermissions);
    await chooseCourse();
    fireEvent.change(await screen.findByLabelText("Assignment to grade"), { target: { value: "2" } });
    expect(await screen.findByText(/another authorized grader/)).toBeVisible();
    expect(screen.queryByRole("button", { name: "Save draft grade" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Release grade/ })).not.toBeInTheDocument();
  });

});
