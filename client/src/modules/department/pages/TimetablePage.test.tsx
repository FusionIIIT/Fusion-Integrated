import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import TimetablePage from "./TimetablePage";
import { api, renderPage, serverError, setup } from "./testUtils";

vi.mock("../../../lib/http", async (orig) => (await import("./testUtils")).httpMock(orig));
vi.mock("../../../auth/AuthProvider", async () => (await import("./testUtils")).authMock());

const SLOT = { id: 1, kind: "class", programme: "B.Tech", batch_year: 2024, course_code: "CS201", day_of_week: 0,
  starts_at: "09:00:00", ends_at: "10:00:00", room: "L-104", updated_at: "2026-11-22" };

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
    setup(["department.timetable.view", "department.timetable.create"], { "/timetable-slots": [] });
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
});
