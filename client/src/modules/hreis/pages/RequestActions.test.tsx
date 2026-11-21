/** Accountant controls appear only when allowed, with financial evidence required. */

import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { HRRequest } from "../api/types";
import { RequestActions } from "./RequestActions";

const auth = vi.hoisted(() => ({ useAuth: vi.fn() }));
const hooks = vi.hoisted(() => ({
  useAssignReviewers: vi.fn(),
  useDecideAppraisal: vi.fn(),
  useDecideRequest: vi.fn(),
  useVerifyClaim: vi.fn(),
  useRecordFinancialProcessing: vi.fn(),
  useVerifyFinancialCorrectness: vi.fn(),
  financialMutation: vi.fn(),
  financialReviewMutation: vi.fn(),
}));
vi.mock("../../../auth/AuthProvider", () => auth);
vi.mock("../api/hooks", () => hooks);

const claim = {
  id: 42,
  user_id: 10,
  family: "ltc",
  subtype: "advance",
  state: "approved",
  payload: { prescribed_form_reference: "official-ltc-form" },
  claim_summary: {
    purpose: "", amount: null, prescribed_form_reference: "official-ltc-form",
    hr_verified: true, financial_verified: false, payment_status: null,
  },
  appraisal_summary: null,
  route_step: 0,
  route_total_steps: 0,
  submitted_at: "2026-11-21T10:00:00Z",
  created_at: "2026-11-21T10:00:00Z",
  updated_at: "2026-11-21T10:00:00Z",
} as HRRequest;

function show(request: HRRequest) {
  return render(<MantineProvider><RequestActions request={request} /></MantineProvider>);
}

describe("HR-EIS Accountant action", () => {
  beforeEach(() => {
    const idle = { isPending: false, mutate: vi.fn() };
    auth.useAuth.mockReturnValue({
      can: (permission: string) => ["hreis.finance.review", "hreis.finance.update"].includes(permission),
    });
    hooks.useAssignReviewers.mockReturnValue(idle);
    hooks.useDecideAppraisal.mockReturnValue(idle);
    hooks.useDecideRequest.mockReturnValue(idle);
    hooks.useVerifyClaim.mockReturnValue(idle);
    hooks.financialMutation.mockReset();
    hooks.useRecordFinancialProcessing.mockReturnValue({
      isPending: false, mutate: hooks.financialMutation,
    });
    hooks.financialReviewMutation.mockReset();
    hooks.useVerifyFinancialCorrectness.mockReturnValue({
      isPending: false, mutate: hooks.financialReviewMutation,
    });
  });

  it("review-only Accountant can attest correctness without updating payment status", async () => {
    auth.useAuth.mockReturnValue({
      can: (permission: string) => permission === "hreis.finance.review",
    });
    show(claim);
    expect(screen.queryByRole("button", { name: "Record finance status" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Verify financial correctness" }));
    expect(await screen.findByText(/does not change payment status or send money/i))
      .toBeInTheDocument();
    fireEvent.change(
      screen.getByRole("textbox", { name: "Financial review evidence reference" }),
      { target: { value: "reviewed-claim-evidence-42" } },
    );
    fireEvent.click(screen.getByRole("button", { name: "Record finance review" }));
    expect(hooks.financialReviewMutation).toHaveBeenCalledWith(
      { id: 42, financial_review_reference: "reviewed-claim-evidence-42" },
      expect.any(Object),
    );
    expect(hooks.financialMutation).not.toHaveBeenCalled();
  });

  it("permits external-status recording but makes clear that it does not pay money", async () => {
    show(claim);
    fireEvent.click(screen.getByRole("button", { name: "Record finance status" }));

    expect(await screen.findByText(/does not send money/i)).toBeInTheDocument();
    fireEvent.change(screen.getByRole("textbox", { name: /financial review evidence reference/i }), {
      target: { value: "signed-check-20" },
    });
    fireEvent.change(screen.getByRole("textbox", { name: /external status reference/i }), {
      target: { value: "finance-status-55" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Record external status" }));

    expect(hooks.financialMutation).toHaveBeenCalledWith(
      {
        id: 42,
        financial_review_reference: "signed-check-20",
        source_system: "finance",
        external_status_reference: "finance-status-55",
        payment_status: "payment_pending",
      },
      expect.objectContaining({
        onSuccess: expect.any(Function), onError: expect.any(Function),
      }),
    );
  });

  it("hides the action from a person without the permission", () => {
    auth.useAuth.mockReturnValue({ can: () => false });
    show(claim);
    expect(screen.queryByRole("button", { name: "Record finance status" })).toBeNull();
  });

  it("does not expose financial processing on unapproved claims", () => {
    show({ ...claim, state: "pending_authority" });
    expect(screen.queryByRole("button", { name: "Record finance status" })).toBeNull();
  });

  it("offers forwarding, not premature approval, at an intermediate route step", async () => {
    auth.useAuth.mockReturnValue({
      can: (permission: string) => permission === "hreis.leave.approve",
    });
    const intermediate: HRRequest = {
      ...claim, family: "leave", state: "pending_authority",
      subtype: "Casual", claim_summary: null, route_step: 0, route_total_steps: 2,
    };
    show(intermediate);
    fireEvent.click(screen.getByRole("button", { name: "Review" }));
    expect(await screen.findByRole("button", { name: "Record decision" })).toBeInTheDocument();
    expect(screen.getByText("Forward to next authority")).toBeInTheDocument();
    expect(screen.queryByText("Approve at final authority")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Record decision" }));
    expect(hooks.useDecideRequest().mutate).toHaveBeenCalledWith(
      expect.objectContaining({ event: "forward" }),
      expect.any(Object),
    );
  });

  it("selects finalization only at the appraisal's final authority", async () => {
    auth.useAuth.mockReturnValue({
      can: (permission: string) => permission === "hreis.appraisal.approve",
    });
    show({
      ...claim,
      family: "appraisal",
      state: "pending_next_appraisal_authority",
      claim_summary: null,
      appraisal_summary: {
        period_key: "FY2026", submitted_form: { summary: "Teaching" },
        reviewer_user_ids: [201],
      },
      route_step: 1, route_total_steps: 2,
    });
    fireEvent.click(screen.getByRole("button", { name: "Review" }));
    expect(await screen.findByText(/Finalize and archive the reviewed appraisal/i))
      .toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Record decision" }));
    expect(hooks.useDecideAppraisal().mutate).toHaveBeenCalledWith(
      expect.objectContaining({ event: "finalize" }), expect.any(Object),
    );
  });

  it("shows the submitted appraisal form to its authorized reviewer", async () => {
    auth.useAuth.mockReturnValue({
      can: (permission: string) => permission === "hreis.appraisal.approve",
    });
    show({
      ...claim,
      family: "appraisal",
      state: "pending_review",
      claim_summary: null,
      appraisal_summary: {
        period_key: "FY2026",
        reviewer_user_ids: [201],
        submitted_form: { yearly_summary: "Verified teaching evidence" },
      },
    });
    fireEvent.click(screen.getByRole("button", { name: "Review" }));
    expect(await screen.findByText("Submitted appraisal form")).toBeInTheDocument();
    expect(screen.getByText(/Verified teaching evidence/)).toBeInTheDocument();
  });
});
