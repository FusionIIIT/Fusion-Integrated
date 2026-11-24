import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import TimetablePage from "./TimetablePage";
import { api, page, renderPage, serverError, setup } from "./testUtils";

vi.mock("../../../lib/http", async (orig) => (await import("./testUtils")).httpMock(orig));
vi.mock("../../../auth/AuthProvider", async () => (await import("./testUtils")).authMock());

const SLOT = { id: 1, kind: "class", programme: "B.Tech", batch_year: 2024, course_code: "CS201", day_of_week: 0,
  starts_at: "09:00:00", ends_at: "10:00:00", room: "L-104", instructor_user_id: null, updated_at: "2026-11-22" };

describe("TimetablePage", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows loading", () => {
    setup([], { "/timetable-slots": "pending" });
    renderPage(<TimetablePage />);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("shows an empty state", async () => {
    setup([], { "/timetable-slots": [] });
    renderPage(<TimetablePage />);
    expect(await screen.findByText("No timetable published yet")).toBeInTheDocument();
  });

  it("shows the error message", async () => {
    setup([], { "/timetable-slots": serverError() });
    renderPage(<TimetablePage />);
    expect(await screen.findByText("Server exploded.")).toBeInTheDocument();
  });

  it("gives a student no editing controls", async () => {
    setup(["department.timetable.view"], { "/timetable-slots": [SLOT] });
    renderPage(<TimetablePage />);
    expect(await screen.findByText("CS201")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Add slot" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Remove" })).toBeNull();
  });

  it("adds a slot and shows the conflict refusal", async () => {
    setup(["department.timetable.view", "department.timetable.create"], { "/timetable-slots": [] }, "dept_admin");
    api.post.mockRejectedValueOnce(serverError("These slots overlap; move them and save again.", 422));
    renderPage(<TimetablePage />);
    fireEvent.click(await screen.findByRole("button", { name: "Add slot" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("Course code"), { target: { value: "CS201" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    expect(await screen.findByText(/These slots overlap/)).toBeInTheDocument();
    await waitFor(() => expect(api.post).toHaveBeenCalledWith("/department/timetable-slots",
      { slots: [expect.objectContaining({ course_code: "CS201", day_of_week: 0 })] }));
  });

  it("sets the slot's instructor from the department's active Faculty", async () => {
    const faculty = { tier: "full", id: 7, kind: "faculty", user_id: 3001, display_name: "Dr. Rao", programme: "",
      department: "CSE", is_active: true };
    const gone = { ...faculty, id: 8, user_id: 3002, display_name: "Dr. Gone", is_active: false };
    setup(["department.timetable.view", "department.timetable.create"],
      { "/timetable-slots": [], "/profiles": page([faculty, gone]) }, "dept_admin");
    api.post.mockResolvedValueOnce({ data: [SLOT] });
    renderPage(<TimetablePage />);
    fireEvent.click(await screen.findByRole("button", { name: "Add slot" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("Course code"), { target: { value: "CS201" } });
    fireEvent.click(within(dialog).getByRole("textbox", { name: "Instructor" }));
    fireEvent.click(await screen.findByText("Dr. Rao"));
    expect(screen.queryByText("Dr. Gone")).toBeNull();
    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    await waitFor(() => expect(api.post).toHaveBeenCalledWith("/department/timetable-slots",
      { slots: [expect.objectContaining({ course_code: "CS201", instructor_user_id: 3001 })] }));
  });

  it("shows the owning office no control its permissions do not allow", async () => {
    setup(["department.timetable.view"], { "/timetable-slots": [SLOT] }, "dept_admin");
    renderPage(<TimetablePage />);
    expect(await screen.findByText("CS201")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Add slot" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Edit" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Remove" })).toBeNull();
  });

  it("shows the server's refusal when removing a slot fails", async () => {
    setup(["department.timetable.view", "department.timetable.update"], { "/timetable-slots": [SLOT] }, "dept_admin");
    api.delete.mockRejectedValueOnce(serverError("That slot was already removed.", 404));
    renderPage(<TimetablePage />);
    fireEvent.click(await screen.findByRole("button", { name: "Remove" }));
    expect(await screen.findByText("That slot was already removed.")).toBeInTheDocument();
  });
});
