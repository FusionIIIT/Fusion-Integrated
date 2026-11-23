import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { authAs, hasLoader, mockHttp, renderPage, serverError } from "../test-utils";
import OversightPage from "./OversightPage";

const auth = vi.hoisted(() => ({ useAuth: vi.fn() }));
vi.mock("../../../auth/AuthProvider", () => auth);

const PERMS = ["pms.workflow.view", "pms.application.view"];
const EMPTY = { next: null, previous: null, results: [] };
const ROW = { id: 7, reference: "PMS-2026-00007", title: "Graphene anode", status: "filed",
  domain_code: "materials", applicant_user_id: 1001, applicant_name: "Asha",
  submitted_at: null, updated_at: "2026-11-02T10:00:00", revision_due_on: null,
  appeal_due_on: null };

describe("OversightPage", () => {
  afterEach(() => vi.restoreAllMocks());

  it("shows a spinner while loading", () => {
    authAs(auth.useAuth, PERMS);
    mockHttp({ oversight: "pending", applications: "pending" });
    const { container } = renderPage(<OversightPage />);
    expect(hasLoader(container)).toBe(true);
  });

  it("shows an empty state", async () => {
    authAs(auth.useAuth, PERMS);
    mockHttp({ oversight: { by_status: {}, total: 0, overdue_reviews: 0, open_escalations: 0 },
      applications: EMPTY });
    renderPage(<OversightPage />);
    expect(await screen.findByText("No applications in your scope")).toBeInTheDocument();
  });

  it("shows the server's message when loading fails", async () => {
    authAs(auth.useAuth, PERMS);
    mockHttp({ oversight: serverError(500, "Counts unavailable."), applications: EMPTY });
    renderPage(<OversightPage />);
    expect(await screen.findByText("Counts unavailable.")).toBeInTheDocument();
  });

  it("shows counts and offers no office actions to a Director", async () => {
    authAs(auth.useAuth, PERMS);
    mockHttp({ oversight: { by_status: { filed: 3 }, total: 3, overdue_reviews: 1,
      open_escalations: 0 }, applications: { ...EMPTY, results: [ROW] } });
    renderPage(<OversightPage />);
    expect(await screen.findByText("Filed")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Assign Director" })).toBeNull();
  });

  it("searches applications by title", async () => {
    authAs(auth.useAuth, PERMS);
    const calls = mockHttp({ oversight: { by_status: {}, total: 1, overdue_reviews: 0,
      open_escalations: 0 }, applications: { ...EMPTY, results: [ROW] } });
    renderPage(<OversightPage />);
    await userEvent.type(await screen.findByRole("textbox", { name: "Search by title or reference" }),
      "anode");
    await waitFor(() => expect(calls.get).toHaveBeenCalledWith("/pms/applications",
      { params: { q: "anode" } }));
  });
});
