import { fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import SchedulesPage from "./SchedulesPage";
import { renderPage, testPageStates } from "../testSupport";

describe("SchedulesPage", () => {
  testPageStates(SchedulesPage, "No doctor schedule slots have been created.");

  it("creates a schedule with the submitted slot fields", async () => {
    const user = userEvent.setup();
    const post = vi.spyOn(http, "post").mockResolvedValue({ data: { id: 4 } } as never);
    renderPage(SchedulesPage);
    await screen.findByText("No doctor schedule slots have been created.");
    await user.type(screen.getByLabelText("Doctor display name"), "Dr. Test");
    await user.type(screen.getByLabelText("Specialization"), "General Medicine");
    fireEvent.change(screen.getByLabelText("Starts at"), { target: { value: "09:00" } });
    fireEvent.change(screen.getByLabelText("Ends at"), { target: { value: "12:00" } });
    await user.click(screen.getByRole("button", { name: "Create schedule" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/phc/doctor-schedules", {
      display_name: "Dr. Test", specialization: "General Medicine", day_of_week: 0,
      starts_at: "09:00", ends_at: "12:00",
    }));
  });

  it("hides create and publish actions without their permissions", async () => {
    renderPage(SchedulesPage, ["phc.doctor_schedule.view"]);
    expect(await screen.findByText("No doctor schedule slots have been created.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Create schedule" })).not.toBeInTheDocument();
  });
});
