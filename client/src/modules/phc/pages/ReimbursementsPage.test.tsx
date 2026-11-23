import { fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import ReimbursementsPage from "./ReimbursementsPage";
import { renderPage, testPageStates } from "../testSupport";

describe("ReimbursementsPage", () => {
  testPageStates(ReimbursementsPage, "No reimbursement claims are available.");

  it("submits a claim linked to the selected prescription", async () => {
    const user = userEvent.setup();
    const post = vi.spyOn(http, "post").mockResolvedValue({ data: { id: 21 } } as never);
    renderPage(ReimbursementsPage, undefined, "default", {
      "/phc/records": { results: [{ id: 4, patient_user_id: 1001,
        visited_on: "2026-11-20", notes: "Visit", recorded_by_user_id: 2,
        created_at: "2026-11-20T00:00:00Z", prescriptions: [{ id: 7,
          details: "Medicine instructions", issued_on: "2026-11-20",
          issued_by_user_id: 2, created_at: "2026-11-20T00:00:00Z" }] }],
        next: null, previous: null },
    });
    await screen.findByText("No reimbursement claims are available.");
    await user.selectOptions(screen.getByLabelText("Prescription"), "7");
    await user.type(screen.getByLabelText("Claim amount"), "125.00");
    fireEvent.change(screen.getByLabelText("Expense date"), {
      target: { value: "2026-11-20" },
    });
    await user.click(screen.getByRole("button", { name: "Submit claim" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/phc/reimbursements", {
      prescription_id: 7, claim_amount: "125", expense_date: "2026-11-20",
      bill_reference: "", remarks: "",
    }));
  });
});
