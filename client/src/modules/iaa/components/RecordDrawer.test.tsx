/** The record drawer shows each role only what its permissions allow, and a decision needs
 *  its remarks. Hooks and the session are replaced; the component is real. */
import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { RecordDetail } from "../api/types";
import { RecordDrawer } from "./RecordDrawer";

const hooks = vi.hoisted(() => ({
  useRecord: vi.fn(), useHistory: vi.fn(), useAddDocument: vi.fn(), useSubmit: vi.fn(),
  useAnswerQuery: vi.fn(), useRaiseQuery: vi.fn(), useValidate: vi.fn(), useDecide: vi.fn(),
  useProcess: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const auth = vi.hoisted(() => ({ useAuth: vi.fn() }));
vi.mock("../../../auth/AuthProvider", () => auth);

vi.mock("./toast", () => ({ done: vi.fn(), failed: vi.fn() }));

const idle = () => ({ mutateAsync: vi.fn().mockResolvedValue({}), isPending: false });
const MUTATIONS = ["useAddDocument", "useSubmit", "useAnswerQuery", "useRaiseQuery",
  "useValidate", "useDecide", "useProcess"] as const;
type Mutation = typeof MUTATIONS[number];
const mutations = Object.fromEntries(MUTATIONS.map((n) => [n, idle()])) as
  Record<Mutation, ReturnType<typeof idle>>;

const record = (over: Partial<RecordDetail> = {}) => ({
  id: 41, kind: "expense", status: "submitted", user_id: 9, department: "CSE",
  request_type: "voucher", title: "Lab kits", description: "Soldering kits", amount: "10000.00",
  purpose: "", trip_start: null, trip_end: null, financial_year: "2026-27",
  submitted_at: null, route_levels: ["iaa_hod"], current_level: 0, processing_reference: "",
  processing_note: "", processed_at: null, created_at: "2026-11-01", updated_at: "2026-11-01",
  documents: [], queries: [], steps: [], ...over,
}) as RecordDetail;

function open(permissions: string[], over: Partial<RecordDetail> = {}, userId = 7) {
  hooks.useRecord.mockReturnValue({ data: record(over), error: null });
  auth.useAuth.mockReturnValue({
    can: (p: string) => permissions.includes(p), session: { user: { id: userId } },
  });
  return render(<MantineProvider><RecordDrawer id={41} onClose={vi.fn()} /></MantineProvider>);
}

beforeEach(() => {
  hooks.useRecord.mockReset();
  hooks.useHistory.mockReset();
  for (const name of MUTATIONS) {
    mutations[name] = idle();
    hooks[name].mockReset();
    hooks[name].mockReturnValue(mutations[name]);
  }
  hooks.useHistory.mockReturnValue({ data: [] });
});

describe("RecordDrawer", () => {
  it("shows the server's failure when the record cannot be loaded", () => {
    hooks.useRecord.mockReturnValue({ data: undefined, error: new Error("down") });
    auth.useAuth.mockReturnValue({ can: () => false, session: { user: { id: 7 } } });
    render(<MantineProvider><RecordDrawer id={41} onClose={vi.fn()} /></MantineProvider>);
    expect(screen.getByText("Could not load this")).toBeInTheDocument();
  });

  it("shows no action at all to a role with no permission", () => {
    open([]);
    expect(screen.queryByRole("button", { name: /submit|validate|record|attach|raise/i }))
      .toBeNull();
  });

  describe("the creator", () => {
    it("can attach a document and submit their own draft", async () => {
      open(["iaa.request.create"], { status: "draft", user_id: 7 });
      expect(screen.getByRole("button", { name: "Attach" })).toBeDisabled();
      await userEvent.click(screen.getByRole("button", { name: "Submit to Finance" }));
      expect(mutations.useSubmit.mutateAsync).toHaveBeenCalledWith(41);
    });

    it("sees no action on someone else's draft", () => {
      open(["iaa.request.create"], { status: "draft", user_id: 9 });
      expect(screen.queryByRole("button", { name: "Submit to Finance" })).toBeNull();
    });

    it("cannot send an empty answer to a clarification query", async () => {
      open(["iaa.request.create"], {
        status: "query_raised", user_id: 7,
        queries: [{ id: 1, question: "Which lab?", raised_role: "iaa_finance_staff",
                    response: "", responded_at: null, created_at: "2026-11-01" }],
      });
      expect(screen.getByText("Finance asks: Which lab?")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Send answer" })).toBeDisabled();
      await userEvent.type(screen.getByLabelText("Your answer"), "Embedded lab");
      await userEvent.click(screen.getByRole("button", { name: "Send answer" }));
      expect(mutations.useAnswerQuery.mutateAsync)
        .toHaveBeenCalledWith({ id: 41, text: "Embedded lab" });
    });
  });

  describe("Finance", () => {
    it("validates a submitted request", async () => {
      open(["iaa.request.review"]);
      await userEvent.click(screen.getByRole("button", { name: "Validate request" }));
      expect(mutations.useValidate.mutateAsync)
        .toHaveBeenCalledWith({ id: 41, decision: "verify", remarks: "" });
    });

    it("cannot raise a query without a question", async () => {
      open(["iaa.request.review"]);
      expect(screen.getByRole("button", { name: "Raise query" })).toBeDisabled();
      await userEvent.type(screen.getByLabelText("Ask the creator (clarification)"), "Which lab?");
      await userEvent.click(screen.getByRole("button", { name: "Raise query" }));
      expect(mutations.useRaiseQuery.mutateAsync)
        .toHaveBeenCalledWith({ id: 41, text: "Which lab?" });
    });

    it("can reject a TA claim only with a reason", async () => {
      open(["iaa.request.review"], { kind: "ta", purpose: "Conference" });
      expect(screen.getByRole("button", { name: "Verify claim" })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Reject (policy)" })).toBeDisabled();
      await userEvent.type(screen.getByLabelText("Remarks"), "Not on duty");
      await userEvent.click(screen.getByRole("button", { name: "Reject (policy)" }));
      expect(mutations.useValidate.mutateAsync)
        .toHaveBeenCalledWith({ id: 41, decision: "reject", remarks: "Not on duty" });
    });

    it("offers no reject-for-policy on an expense request", () => {
      open(["iaa.request.review"]);
      expect(screen.queryByRole("button", { name: "Reject (policy)" })).toBeNull();
    });

    it("records an approved item with a reference, and says no payment is made", async () => {
      open(["iaa.processing.create"], { status: "approved" });
      expect(screen.getByText(/No payment is made/)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Record processing" })).toBeDisabled();
      await userEvent.type(screen.getByLabelText("Processing reference"), "VCH-1");
      await userEvent.click(screen.getByRole("button", { name: "Record processing" }));
      expect(mutations.useProcess.mutateAsync)
        .toHaveBeenCalledWith({ id: 41, reference: "VCH-1", note: "" });
    });

    it("cannot validate without the review permission", () => {
      open(["iaa.processing.create"]);
      expect(screen.queryByRole("button", { name: "Validate request" })).toBeNull();
    });
  });

  describe("an approving authority", () => {
    it("cannot decide without remarks", async () => {
      open(["iaa.request.approve"], { status: "finance_validated" });
      expect(screen.getByRole("button", { name: "Record decision" })).toBeDisabled();
      await userEvent.type(screen.getByLabelText("Remarks (required)"), "Within plan");
      await userEvent.click(screen.getByRole("button", { name: "Record decision" }));
      expect(mutations.useDecide.mutateAsync)
        .toHaveBeenCalledWith({ id: 41, decision: "approve", remarks: "Within plan" });
    });

    it("can reject, with remarks", async () => {
      open(["iaa.request.approve"], { status: "escalated" });
      await userEvent.click(screen.getByText("Reject"));
      await userEvent.type(screen.getByLabelText("Remarks (required)"), "Not justified");
      await userEvent.click(screen.getByRole("button", { name: "Record decision" }));
      expect(mutations.useDecide.mutateAsync)
        .toHaveBeenCalledWith({ id: 41, decision: "reject", remarks: "Not justified" });
    });

    it("sees no decision form on an item that is not waiting on an authority", () => {
      open(["iaa.request.approve"], { status: "recorded" });
      expect(screen.queryByRole("button", { name: "Record decision" })).toBeNull();
    });

    it("sees no decision form without the approve permission", () => {
      open(["iaa.request.view"], { status: "finance_validated" });
      expect(screen.queryByRole("button", { name: "Record decision" })).toBeNull();
    });
  });
});
