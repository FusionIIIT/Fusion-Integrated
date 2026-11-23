import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import AttendancePage from "./AttendancePage";
import { renderPage, testPageStates } from "../testSupport";

describe("AttendancePage", () => {
  testPageStates(AttendancePage, "No doctor attendance has been recorded today.");

  it("records the selected doctor's availability", async () => {
    const user = userEvent.setup();
    const post = vi.spyOn(http, "post").mockResolvedValue({ data: { id: 7 } } as never);
    renderPage(AttendancePage, undefined, "default", {
      "/phc/doctor-schedules": { results: [{ id: 3, doctor: {
        id: 9, display_name: "Dr. Example", specialization: "General Medicine",
        is_active: true,
      }, day_of_week: 1, starts_at: "09:00:00", ends_at: "12:00:00",
      publication: "published" }], next: null, previous: null },
    });
    await user.selectOptions(await screen.findByLabelText("Doctor"), "9");
    await user.click(screen.getByRole("button", { name: "Save attendance" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/phc/doctor-attendance", {
      doctor_id: 9, status: "available",
    }));
  });
});
