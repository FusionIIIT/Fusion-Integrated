import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { authAs, hasLoader, mockHttp, renderPage, serverError } from "../test-utils";
import ApplicationsPage from "./ApplicationsPage";

const auth = vi.hoisted(() => ({ useAuth: vi.fn() }));
vi.mock("../../../auth/AuthProvider", () => auth);

const APPLICANT = ["pms.application.view", "pms.application.create", "pms.application.update"];
const ROW = { id: 7, reference: "PMS-2026-00007", title: "Graphene anode", status: "submitted",
  domain_code: "materials", applicant_user_id: 1001, applicant_name: "Asha",
  submitted_at: "2026-11-02T10:00:00", updated_at: "2026-11-02T10:00:00",
  revision_due_on: null, appeal_due_on: null };

describe("ApplicationsPage", () => {
  afterEach(() => vi.restoreAllMocks());

  it("shows a spinner while loading", () => {
    authAs(auth.useAuth, APPLICANT);
    mockHttp({ applications: "pending", "my-work": "pending" });
    const { container } = renderPage(<ApplicationsPage />);
    expect(hasLoader(container)).toBe(true);
  });

  it("shows an empty state", async () => {
    authAs(auth.useAuth, APPLICANT);
    mockHttp({ applications: { next: null, previous: null, results: [] }, "my-work": [] });
    renderPage(<ApplicationsPage />);
    expect(await screen.findByText("No applications yet")).toBeInTheDocument();
  });

  it("shows the server's message when the list fails", async () => {
    authAs(auth.useAuth, APPLICANT);
    mockHttp({ applications: serverError(500, "Database unavailable."), "my-work": [] });
    renderPage(<ApplicationsPage />);
    expect(await screen.findByText("Database unavailable.")).toBeInTheDocument();
  });

  it("offers no New application to a role that cannot create one", async () => {
    authAs(auth.useAuth, ["pms.application.view"]);
    mockHttp({ applications: { next: null, previous: null, results: [ROW] }, "my-work": [] });
    renderPage(<ApplicationsPage />);
    expect(await screen.findByText("Graphene anode")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "New application" })).toBeNull();
  });

  it("starts a draft and shows the server's refusal when it says no", async () => {
    authAs(auth.useAuth, APPLICANT);
    const calls = mockHttp(
      { applications: { next: null, previous: null, results: [] }, "my-work": [],
        "reference-data": { domains: [{ code: "materials", label: "Materials",
          ipc_classes: [] }] } },
      { applications: serverError(409, "Too many drafts; finish one first.") });
    renderPage(<ApplicationsPage />);
    await userEvent.click(await screen.findByRole("button", { name: "New application" }));
    await userEvent.type(screen.getByRole("textbox", { name: "Title" }), "Graphene anode");
    await userEvent.click(screen.getByRole("button", { name: "Save draft" }));
    await waitFor(() => expect(calls.post).toHaveBeenCalledWith("/pms/applications",
      expect.objectContaining({ title: "Graphene anode" })));
    expect(await screen.findByText("Too many drafts; finish one first.")).toBeInTheDocument();
  });
});
