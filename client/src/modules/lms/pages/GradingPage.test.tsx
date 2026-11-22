import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { chooseCourse, facultyPermissions, mockReads, pageOf, renderLms } from "../test-support";
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
});
