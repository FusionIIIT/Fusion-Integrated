import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { authAs, hasLoader, mockHttp, renderPage, serverError } from "../test-utils";
import ReviewsPage from "./ReviewsPage";

const auth = vi.hoisted(() => ({ useAuth: vi.fn() }));
vi.mock("../../../auth/AuthProvider", () => auth);

const PERMS = ["pms.application.view", "pms.review.approve"];
const ME = 2001;

const ITEM = { kind: "review", id: 7, application_id: 7, reference: "PMS-2026-00007",
  title: "Graphene anode", status: "open" };
const EMPTY_PAGE = { next: null, previous: null, results: [] };
const DETAIL = { id: 7, reference: "PMS-2026-00007", title: "Graphene anode", status: "under_review",
  domain_code: "materials", applicant_user_id: 1001, applicant_name: "Asha",
  submitted_at: null, updated_at: "2026-11-02T10:00:00", revision_due_on: null,
  appeal_due_on: null, abstract: "", description: "", claims: "", preferred_attorney_user_id: null,
  version: 1, decided_on: null, grant_date: null, grant_jurisdiction: "", patent_number: "",
  inventors: [], review_cycles: [{ id: 1, cycle_no: 1, director_user_id: 2001, director_name: "D", assigned_on: "2026-11-01", due_on: "2026-11-22", status: "open", decision: "", justification: "", decided_at: null }], appeals: [], attorney_assignments: [],
  budgets: [], filings: [], communications: [], office_actions: [], maintenance_cycles: [],
  assessments: [], legal_requests: [], legal_advice: [], revision_responses: [],
  relations: [], feedback: {} };

describe("ReviewsPage", () => {
  afterEach(() => vi.restoreAllMocks());

  it("shows a spinner while loading", () => {
    authAs(auth.useAuth, PERMS, ME);
    mockHttp({ "my-work": "pending", applications: "pending" });
    const { container } = renderPage(<ReviewsPage />);
    expect(hasLoader(container)).toBe(true);
  });

  it("shows an empty state", async () => {
    authAs(auth.useAuth, PERMS, ME);
    mockHttp({ "my-work": [], applications: EMPTY_PAGE });
    renderPage(<ReviewsPage />);
    expect(await screen.findByText("No decisions are waiting on you")).toBeInTheDocument();
  });

  it("shows the server's message when loading fails", async () => {
    authAs(auth.useAuth, PERMS, ME);
    mockHttp({ "my-work": serverError(500, "Queue unavailable."), applications: EMPTY_PAGE });
    renderPage(<ReviewsPage />);
    expect(await screen.findByText("Queue unavailable.")).toBeInTheDocument();
  });

  it("hides the action from a role without its permission", async () => {
    authAs(auth.useAuth, ["pms.application.view"], ME);
    mockHttp({ "my-work": [ITEM], applications: EMPTY_PAGE, "applications/7": DETAIL });
    renderPage(<ReviewsPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Open PMS-2026-00007" }));
    expect(await screen.findAllByText(/Graphene anode/)).not.toHaveLength(0);
    expect(screen.queryByRole("button", { name: "Record decision" })).toBeNull();
  });

  it("records a decision and shows the server's refusal", async () => {
    authAs(auth.useAuth, PERMS, ME);
    const calls = mockHttp({ "my-work": [ITEM], applications: EMPTY_PAGE, "applications/7": DETAIL,
       }, { "applications/7/review": serverError(409, "The review deadline was 2026-11-22.") });
    renderPage(<ReviewsPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Open PMS-2026-00007" }));
    await userEvent.click(await screen.findByRole("button", { name: "Record decision" }));
    await userEvent.click(screen.getByRole("textbox", { name: "Decision" }));
    await userEvent.click(await screen.findByRole("option", { name: "Approve", hidden: true }));
    await userEvent.type(screen.getByRole("textbox", { name: /Justification/ }), "x".repeat(60));
    await userEvent.click(screen.getByRole("button", { name: "Record decision" }));
    await waitFor(() => expect(calls.post).toHaveBeenCalledWith("/pms/applications/7/review",
      expect.objectContaining({ decision: "approve" })));
    expect(await screen.findByText("The review deadline was 2026-11-22.")).toBeInTheDocument();
  });
});
