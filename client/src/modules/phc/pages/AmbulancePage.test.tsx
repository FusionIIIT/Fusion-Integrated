import { fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import AmbulancePage from "./AmbulancePage";
import { renderPage, testPageStates } from "../testSupport";

describe("AmbulancePage", () => {
  testPageStates(AmbulancePage, "No ambulance usage has been recorded.");

  it("records a patient destination and event timestamp", async () => {
    const user = userEvent.setup();
    const post = vi.spyOn(http, "post").mockResolvedValue({ data: { id: 8 } } as never);
    renderPage(AmbulancePage);
    await screen.findByText("No ambulance usage has been recorded.");
    fireEvent.change(screen.getByLabelText("Time used"), {
      target: { value: "2026-11-23T10:30" },
    });
    await user.type(screen.getByLabelText("Patient name"), "Test Patient");
    await user.type(screen.getByLabelText("Destination"), "City Hospital");
    await user.click(screen.getByRole("button", { name: "Record ambulance use" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/phc/ambulance-usage", {
      used_at: new Date("2026-11-23T10:30").toISOString(),
      patient_name: "Test Patient", destination: "City Hospital",
    }));
  });
});
