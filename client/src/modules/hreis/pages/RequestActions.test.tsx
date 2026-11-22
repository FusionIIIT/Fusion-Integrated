import { access, boundary, claim, resetBoundary, show, unavailable } from "./testSupport";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import type { HRRequest } from "../api/types";
import { RequestActions } from "./RequestActions";

describe("Accountant and authority mutations through HTTP", () => {
  beforeEach(() => { resetBoundary(); access.permissions = ["hreis.finance.review", "hreis.finance.update"]; });
  it("review-only Accountant attests correctness without external status write rights", async () => {
    access.permissions = ["hreis.finance.review"];
    show(<RequestActions request={claim} />);
    expect(screen.queryByRole("button", { name: "Record finance status" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Verify financial correctness" }));
    fireEvent.change(await screen.findByRole("textbox", { name: "Financial review evidence reference" }), { target: { value: "signed-review" } });
    fireEvent.click(screen.getByRole("button", { name: "Record finance review" }));
    await waitFor(() => expect(boundary.post).toHaveBeenCalledWith("/hreis/requests/42/financial-review/",
      { financial_review_reference: "signed-review" }, { headers: { "Idempotency-Key": expect.any(String) } }));
    expect(await screen.findByText("Workflow updated")).toBeInTheDocument();
  });
  it("records a reported external status with its evidence", async () => {
    show(<RequestActions request={claim} />);
    fireEvent.click(screen.getByRole("button", { name: "Record finance status" }));
    expect(await screen.findByText(/does not send money/i)).toBeInTheDocument();
    fireEvent.change(screen.getByRole("textbox", { name: /financial review evidence reference/i }), { target: { value: "signed-review" } });
    fireEvent.change(screen.getByRole("textbox", { name: /external status reference/i }), { target: { value: "finance-report" } });
    fireEvent.click(screen.getByRole("button", { name: "Record external status" }));
    await waitFor(() => expect(boundary.post).toHaveBeenCalledWith("/hreis/requests/42/financial-processing/", {
      financial_review_reference: "signed-review", source_system: "finance",
      external_status_reference: "finance-report", payment_status: "payment_pending",
    }, expect.any(Object)));
  });
  it("records processing before an external report and preserves server rejection feedback", async () => {
    boundary.post.mockRejectedValue(unavailable);
    show(<RequestActions request={claim} />);
    fireEvent.click(screen.getByRole("button", { name: "Record finance status" }));
    fireEvent.change(await screen.findByRole("textbox", { name: /financial review evidence reference/i }), { target: { value: "signed-review" } });
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: "Record financial processing" }));
    expect(await screen.findByText("Synthetic service unavailable. Retry shortly.")).toBeInTheDocument();
    expect(boundary.post).toHaveBeenCalledWith("/hreis/requests/42/financial-processing/",
      expect.objectContaining({ financial_review_reference: "signed-review", payment_status: undefined }), expect.any(Object));
    expect(screen.queryByRole("textbox", { name: /external status reference/i })).toBeNull();
  });
  it("hides processing from unauthorized roles and unapproved claims", () => {
    access.permissions = [];
    const hidden = show(<RequestActions request={claim} />);
    expect(screen.queryByRole("button", { name: "Record finance status" })).toBeNull();
    hidden.unmount();
    access.permissions = ["hreis.finance.update"];
    show(<RequestActions request={{ ...claim, state: "pending_authority" }} />);
    expect(screen.queryByRole("button", { name: "Record finance status" })).toBeNull();
  });
  it("forwards only at an intermediate authority", async () => {
    access.permissions = ["hreis.leave.approve"];
    show(<RequestActions request={{ ...claim, family: "leave", state: "pending_authority", claim_summary: null,
      subtype: "Casual", route_step: 0, route_total_steps: 2 }} />);
    fireEvent.click(screen.getByRole("button", { name: "Review" }));
    expect(await screen.findByText("Forward to next authority")).toBeInTheDocument();
    expect(screen.queryByText("Approve at final authority")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Record decision" }));
    await waitFor(() => expect(boundary.post).toHaveBeenCalledWith("/hreis/requests/42/decision/",
      { event: "forward", reason: "" }, expect.any(Object)));
  });
  it("shows the submitted form and finalizes only at the final appraisal authority", async () => {
    access.permissions = ["hreis.appraisal.approve"];
    const appraisal: HRRequest = { ...claim, family: "appraisal", state: "pending_next_appraisal_authority",
      claim_summary: null, appraisal_summary: { period_key: "FY2026", reviewer_user_ids: [201],
        submitted_form: { summary: "Verified teaching evidence" } }, route_step: 1, route_total_steps: 2 };
    show(<RequestActions request={appraisal} />);
    fireEvent.click(screen.getByRole("button", { name: "Review" }));
    expect(await screen.findByText(/Verified teaching evidence/)).toBeInTheDocument();
    expect(screen.getByText(/Finalize and archive the reviewed appraisal/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Record decision" }));
    await waitFor(() => expect(boundary.post).toHaveBeenCalledWith("/hreis/requests/42/appraisal-decision/",
      { event: "finalize" }, expect.any(Object)));
  });
});
