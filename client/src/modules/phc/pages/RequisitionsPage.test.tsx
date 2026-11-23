import { fireEvent, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import RequisitionsPage from "./RequisitionsPage";
import { listStateTests, refusal, renderPage, state } from "./testing";

const http = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn() }));
vi.mock("../../../lib/http", async (orig) => ({
  ...(await orig<typeof import("../../../lib/http")>()), http,
}));
vi.mock("../../../auth/AuthProvider", () => ({
  useAuth: () => ({ can: (p: string) => state.permissions.has(p) }),
}));

const req = { id: 4, originator_user_id: 3001, purpose: "Monthly restock",
  status: "pending_approval", status_label: "Pending approval",
  lines: [{ item: 5, item_name: "Paracetamol 500mg", unit: "strip", quantity: "200.00" }],
  decision_note: "", decided_at: null, fulfilled_at: null,
  created_at: "2026-11-23T12:30:00Z", allowed_events: ["approve", "reject"] };
const page = (rows: unknown[]) => ({ results: rows, next: null, previous: null });

describe("RequisitionsPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    state.permissions = new Set(["phc.requisition.view"]);
  });

  listStateTests({ get: http.get, page: () => <RequisitionsPage />, empty: page([]),
    emptyText: /no requisitions/i });

  it("hides the new-requisition button from the authority", async () => {
    state.permissions.add("phc.requisition.approve");
    http.get.mockResolvedValue({ data: page([req]) });
    renderPage(<RequisitionsPage />);
    expect(await screen.findByRole("button", { name: "Approve" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /new requisition/i })).not.toBeInTheDocument();
  });

  it("the authority approves and sees a refusal", async () => {
    state.permissions.add("phc.requisition.approve");
    http.get.mockResolvedValue({ data: page([req]) });
    http.post.mockRejectedValueOnce(refusal("This requisition is already approved.", 409));
    renderPage(<RequisitionsPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Approve" }));
    expect(await screen.findByText("This requisition is already approved.")).toBeInTheDocument();
    expect(http.post).toHaveBeenCalledWith("/phc/requisitions/4/transition",
      { event: "approve", note: "" });
  });

  it("PHC staff open the new requisition form", async () => {
    state.permissions.add("phc.requisition.create");
    http.get.mockResolvedValue({ data: page([]) });
    renderPage(<RequisitionsPage />);
    fireEvent.click(await screen.findByRole("button", { name: /new requisition/i }));
    expect(await screen.findByLabelText(/purpose/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Submit" })).toBeDisabled();
  });
});
