import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { authAs, hasLoader, mockHttp, renderPage, serverError } from "../test-utils";
import CasesPage from "./CasesPage";

const auth = vi.hoisted(() => ({ useAuth: vi.fn() }));
vi.mock("../../../auth/AuthProvider", () => auth);

const PERMS = ["pms.application.view", "pms.attorney_assignment.review"];
const ME = 3001;

const ITEM = { kind: "case", id: 7, application_id: 7, reference: "PMS-2026-00007",
  title: "Graphene anode", status: "offered" };
const EMPTY_PAGE = { next: null, previous: null, results: [] };
const DETAIL = { id: 7, reference: "PMS-2026-00007", title: "Graphene anode", status: "approved",
  domain_code: "materials", applicant_user_id: 1001, applicant_name: "Asha",
  submitted_at: null, updated_at: "2026-11-02T10:00:00", revision_due_on: null,
  appeal_due_on: null, abstract: "", description: "", claims: "", preferred_attorney_user_id: null,
  version: 1, decided_on: null, grant_date: null, grant_jurisdiction: "", patent_number: "",
  inventors: [], review_cycles: [], appeals: [], attorney_assignments: [{ id: 9, application_id: 7, application_reference: "PMS-2026-00007", application_title: "Graphene anode", attorney_user_id: 3001, attorney_name: "A", is_exception: false, exception_reason: "", status: "offered", responded_at: null, decline_reason: "", created_at: "2026-11-01" }],
  budgets: [], filings: [], communications: [], office_actions: [], maintenance_cycles: [],
  assessments: [], legal_requests: [], legal_advice: [], revision_responses: [],
  relations: [], feedback: {} };

describe("CasesPage", () => {
  afterEach(() => vi.restoreAllMocks());

  it("shows a spinner while loading", () => {
    authAs(auth.useAuth, PERMS, ME);
    mockHttp({ "my-work": "pending", applications: "pending" });
    const { container } = renderPage(<CasesPage />);
    expect(hasLoader(container)).toBe(true);
  });

  it("shows an empty state", async () => {
    authAs(auth.useAuth, PERMS, ME);
    mockHttp({ "my-work": [], applications: EMPTY_PAGE });
    renderPage(<CasesPage />);
    expect(await screen.findByText("No cases are offered or open")).toBeInTheDocument();
  });

  it("shows the server's message when loading fails", async () => {
    authAs(auth.useAuth, PERMS, ME);
    mockHttp({ "my-work": serverError(500, "Queue unavailable."), applications: EMPTY_PAGE });
    renderPage(<CasesPage />);
    expect(await screen.findByText("Queue unavailable.")).toBeInTheDocument();
  });

  it("hides the action from a role without its permission", async () => {
    authAs(auth.useAuth, ["pms.application.view"], ME);
    mockHttp({ "my-work": [ITEM], applications: EMPTY_PAGE, "applications/7": DETAIL });
    renderPage(<CasesPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Open PMS-2026-00007" }));
    expect(await screen.findAllByText(/Graphene anode/)).not.toHaveLength(0);
    expect(screen.queryByRole("button", { name: "Accept case" })).toBeNull();
  });

  it("accepts a case and shows the server's refusal", async () => {
    authAs(auth.useAuth, PERMS, ME);
    const calls = mockHttp({ "my-work": [ITEM], applications: EMPTY_PAGE, "applications/7": DETAIL,
       }, { "attorney-assignments/9/respond": serverError(409, "This offer was withdrawn.") });
    renderPage(<CasesPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Open PMS-2026-00007" }));
    await userEvent.click(await screen.findByRole("button", { name: "Accept case" }));

    await userEvent.click(screen.getByRole("button", { name: "Accept" }));
    await waitFor(() => expect(calls.post).toHaveBeenCalledWith("/pms/attorney-assignments/9/respond",
      expect.objectContaining({ accept: true })));
    expect(await screen.findByText("This offer was withdrawn.")).toBeInTheDocument();
  });
});
