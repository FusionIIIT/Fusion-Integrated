import { fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { chooseCourse, facultyPermissions, mockReads, pageOf, renderLms } from "../test-support";
import TeachingPage from "./TeachingPage";

afterEach(() => vi.restoreAllMocks());
describe("TeachingPage", () => {
  it("shows loading", async () => {
    vi.spyOn(http, "get").mockReturnValue(new Promise(() => undefined));
    renderLms(<TeachingPage />, facultyPermissions);
    expect(await screen.findByRole("status")).toBeVisible();
  });
  it("shows no assigned courses", async () => {
    mockReads({ "/lms/courses/": pageOf([]) });
    renderLms(<TeachingPage />, facultyPermissions);
    expect(await screen.findByText(/No linked courses/)).toBeVisible();
  });
  it("shows an error instead of a permanent spinner", async () => {
    vi.spyOn(http, "get").mockRejectedValue({ response: { status: 500, data: { error: { message: "Teaching unavailable" } } } });
    renderLms(<TeachingPage />, facultyPermissions);
    expect(await screen.findByRole("alert")).toHaveTextContent("Teaching unavailable");
  });
  it("does not mount or fetch for a role without the route permission", async () => {
    mockReads();
    renderLms(<TeachingPage />, ["lms.course.view"], "lms.course.update");
    expect(await screen.findByText(/Not available to your role/i)).toBeVisible();
    expect(screen.queryByRole("button", { name: "Create assignment draft" })).not.toBeInTheDocument();
    expect(http.get).not.toHaveBeenCalled();
  });
  it("publishes updated course details", async () => {
    mockReads();
    vi.spyOn(http, "patch").mockResolvedValue({ data: {} });
    renderLms(<TeachingPage />, facultyPermissions);
    await chooseCourse();
    fireEvent.change(await screen.findByLabelText("Syllabus"), { target: { value: "Revised syllabus" } });
    fireEvent.click(screen.getByRole("button", { name: "Publish course details" }));
    await waitFor(() => expect(http.patch).toHaveBeenCalledWith("/lms/courses/1/", { syllabus: "Revised syllabus", schedule: "Monday" }));
    expect(await screen.findByText("Saved successfully.")).toBeVisible();
  });
});
