import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ClaimsPage from "./ClaimsPage";
import { listStateTests, refusal, renderPage, state } from "./testing";

const http = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn() }));
vi.mock("../../../lib/http", async (orig) => ({
  ...(await orig<typeof import("../../../lib/http")>()), http,
}));
vi.mock("../../../auth/AuthProvider", () => ({
  useAuth: () => ({ can: (p: string) => state.permissions.has(p) }),
}));

const claim = { id: 7, user_id: 2001, prescription: 17,
  prescription_label: "Paracetamol 500mg (2026-11-21)", expense_date: "2026-11-21",
  amount: "450.00", description: "", status: "pending_phc_review",
  status_label: "Pending PHC review", submitted_at: "2026-11-22T11:00:00Z",
  actions: [{ event: "submit", from_status: "", to_status: "pending_phc_review", note: "",
    created_at: "2026-11-22T11:00:00Z" }], allowed_events: [] as string[] };
const page = (rows: unknown[]) => ({ results: rows, next: null, previous: null });

describe("ClaimsPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    state.permissions = new Set(["phc.claim.view", "phc.claim.create"]);
  });

  listStateTests({ get: http.get, page: () => <ClaimsPage />, empty: page([]),
    emptyText: /no reimbursement claims/i });

  it("shows the employee status and history but no processing buttons", async () => {
    http.get.mockResolvedValue({ data: page([claim]) });
    renderPage(<ClaimsPage />);
    expect(await screen.findByText("Pending PHC review")).toBeInTheDocument();
    expect(screen.getByText("submit")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /forward/i })).not.toBeInTheDocument();
  });

  it("hides the new-claim button from an office without phc.claim.create", async () => {
    state.permissions = new Set(["phc.claim.view", "phc.claim.review"]);
    http.get.mockResolvedValue({ data: page([{ ...claim, allowed_events: ["forward"] }]) });
    renderPage(<ClaimsPage />);
    expect(await screen.findByRole("button", { name: /forward to accounts/i }))
      .toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /new claim/i })).not.toBeInTheDocument();
  });

  it("submits a claim and shows the server's refusal", async () => {
    http.get.mockImplementation((url: string) => Promise.resolve({
      data: url === "/phc/claims/prescriptions"
        ? [{ id: 17, medicine: "Paracetamol 500mg", dosage: "1-0-1", visit_date: "2026-11-21" }]
        : page([]) }));
    http.post.mockRejectedValueOnce(refusal(
      "Claims must be submitted within 30 days of the medical expense date."));
    renderPage(<ClaimsPage />);
    fireEvent.click(await screen.findByRole("button", { name: /new claim/i }));
    await waitFor(() => expect(http.get).toHaveBeenCalledWith("/phc/claims/prescriptions"));
    const picker = await screen.findByRole("textbox", { name: "Prescription" });
    const option = await waitFor(() => {
      fireEvent.click(picker);
      return screen.getByRole("option", { name: /paracetamol 500mg/i, hidden: true });
    });
    fireEvent.click(option);
    fireEvent.change(screen.getByLabelText(/medical expense date/i),
      { target: { value: "2026-10-01" } });
    fireEvent.change(screen.getByLabelText(/amount/i), { target: { value: "450" } });
    fireEvent.click(screen.getByRole("button", { name: /submit claim/i }));
    expect(await screen.findByText(
      "Claims must be submitted within 30 days of the medical expense date.")).toBeInTheDocument();
    expect(http.post).toHaveBeenCalledWith("/phc/claims", { prescription_id: 17,
      expense_date: "2026-10-01", amount: "450", description: "" });
  });

  it("an office forwards a claim", async () => {
    state.permissions = new Set(["phc.claim.view", "phc.claim.review"]);
    http.get.mockResolvedValue({ data: page([{ ...claim, allowed_events: ["forward"] }]) });
    http.post.mockRejectedValueOnce(refusal("This claim cannot be forwarded now.", 409));
    renderPage(<ClaimsPage />);
    fireEvent.click(await screen.findByRole("button", { name: /forward to accounts/i }));
    expect(await screen.findByText("This claim cannot be forwarded now.")).toBeInTheDocument();
    expect(http.post).toHaveBeenCalledWith("/phc/claims/7/transition",
      { event: "forward", note: "" });
  });
});
