import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import MedicalRecordsPage from "./MedicalRecordsPage";
import { renderPage, testPageStates } from "../testSupport";

describe("MedicalRecordsPage", () => {
  testPageStates(MedicalRecordsPage, "No medical visits are recorded yet.");

  it("downloads only the selected visit records through the shared HTTP client", async () => {
    const user = userEvent.setup();
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:medical-record");
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
    const post = vi.spyOn(http, "post").mockResolvedValue({
      data: new Blob(["pdf"]), headers: { "content-disposition": "attachment; filename=record.pdf" },
    } as never);
    renderPage(MedicalRecordsPage, undefined, "default", {
      "/phc/records": { results: [{ id: 9, patient_user_id: 1001,
        visited_on: "2026-11-20", notes: "Visit notes", recorded_by_user_id: 2,
        prescriptions: [], created_at: "2026-11-20T00:00:00Z" }], next: null, previous: null },
    });
    await user.click(await screen.findByRole("checkbox", { name: "Include visit from 2026-11-20" }));
    await user.click(screen.getByRole("button", { name: "Download selected records as PDF" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/phc/records/pdf",
      { visit_ids: [9] }, { responseType: "blob" }));
  });
});
