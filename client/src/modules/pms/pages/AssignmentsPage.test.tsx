import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { authAs, hasLoader, mockHttp, renderPage, serverError } from "../test-utils";
import AssignmentsPage from "./AssignmentsPage";

const auth = vi.hoisted(() => ({ useAuth: vi.fn() }));
vi.mock("../../../auth/AuthProvider", () => auth);

const PERMS = ["pms.application.view", "pms.review.assign"];
const ME = 4001;

const ITEM = { kind: "assign_director", id: 7, application_id: 7, reference: "PMS-2026-00007",
  title: "Graphene anode", status: "submitted" };
const EMPTY_PAGE = { next: null, previous: null, results: [] };
const DETAIL = { id: 7, reference: "PMS-2026-00007", title: "Graphene anode", status: "submitted",
  domain_code: "materials", applicant_user_id: 1001, applicant_name: "Asha",
  submitted_at: null, updated_at: "2026-11-02T10:00:00", revision_due_on: null,
  appeal_due_on: null, abstract: "", description: "", claims: "", preferred_attorney_user_id: null,
  version: 1, decided_on: null, grant_date: null, grant_jurisdiction: "", patent_number: "",
  inventors: [], review_cycles: [], appeals: [], attorney_assignments: [],
  budgets: [], filings: [], communications: [], office_actions: [], maintenance_cycles: [],
  assessments: [], legal_requests: [], legal_advice: [], revision_responses: [],
  relations: [], feedback: {} };

describe("AssignmentsPage", () => {
  afterEach(() => vi.restoreAllMocks());

  it("shows a spinner while loading", () => {
    authAs(auth.useAuth, PERMS, ME);
    mockHttp({ "my-work": "pending", applications: "pending" });
    const { container } = renderPage(<AssignmentsPage />);
    expect(hasLoader(container)).toBe(true);
  });

  it("shows an empty state", async () => {
    authAs(auth.useAuth, PERMS, ME);
    mockHttp({ "my-work": [], applications: EMPTY_PAGE });
    renderPage(<AssignmentsPage />);
    expect(await screen.findByText("Nothing is waiting to be assigned")).toBeInTheDocument();
  });

  it("shows the server's message when loading fails", async () => {
    authAs(auth.useAuth, PERMS, ME);
    mockHttp({ "my-work": serverError(500, "Queue unavailable."), applications: EMPTY_PAGE });
    renderPage(<AssignmentsPage />);
    expect(await screen.findByText("Queue unavailable.")).toBeInTheDocument();
  });

  it("hides the action from a role without its permission", async () => {
    authAs(auth.useAuth, ["pms.application.view"], ME);
    mockHttp({ "my-work": [ITEM], applications: EMPTY_PAGE, "applications/7": DETAIL });
    renderPage(<AssignmentsPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Open PMS-2026-00007" }));
    expect(await screen.findAllByText(/Graphene anode/)).not.toHaveLength(0);
    expect(screen.queryByRole("button", { name: "Assign Director" })).toBeNull();
  });

  it("assigns a Director and shows the server's refusal", async () => {
    authAs(auth.useAuth, PERMS, ME);
    const calls = mockHttp({ "my-work": [ITEM], applications: EMPTY_PAGE, "applications/7": DETAIL,
      "applications/7/director-candidates": [{ user_id: 2001, name: "Dr Rao", domain_codes: ["materials"], workload: 0 }] }, { "applications/7/assign-director": serverError(409, "That Director is an inventor.") });
    renderPage(<AssignmentsPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Open PMS-2026-00007" }));
    await userEvent.click(await screen.findByRole("button", { name: "Assign Director" }));
    await userEvent.click(screen.getByRole("textbox", { name: "Director" }));
    await userEvent.click(await screen.findByRole("option", { name: /Dr Rao/, hidden: true }));
    await userEvent.click(screen.getByRole("button", { name: "Assign" }));
    await waitFor(() => expect(calls.post).toHaveBeenCalledWith("/pms/applications/7/assign-director",
      expect.objectContaining({ director_user_id: 2001 })));
    expect(await screen.findByText("That Director is an inventor.")).toBeInTheDocument();
  });
});
