import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { authAs, hasLoader, mockHttp, renderPage, serverError } from "../test-utils";
import AuditPage from "./AuditPage";

const auth = vi.hoisted(() => ({ useAuth: vi.fn() }));
vi.mock("../../../auth/AuthProvider", () => auth);

const PCC = ["pms.audit_log.view", "pms.audit_log.export"];
const EMPTY = { next: null, previous: null, results: [] };
const ENTRY = { id: 1, at: "2026-11-02T10:00:00", actor_user_id: 1001, actor_role: "student",
  action: "application.submit", application_id: 7, application_reference: "PMS-2026-00007",
  object_type: "Application", object_id: 7, from_state: "draft", to_state: "submitted",
  details: {} };

describe("AuditPage", () => {
  afterEach(() => vi.restoreAllMocks());

  it("shows a spinner while loading", () => {
    authAs(auth.useAuth, PCC);
    mockHttp({ audit: "pending" });
    const { container } = renderPage(<AuditPage />);
    expect(hasLoader(container)).toBe(true);
  });

  it("shows an empty state", async () => {
    authAs(auth.useAuth, PCC);
    mockHttp({ audit: EMPTY });
    renderPage(<AuditPage />);
    expect(await screen.findByText("No audit entries")).toBeInTheDocument();
  });

  it("shows the server's message when loading fails", async () => {
    authAs(auth.useAuth, PCC);
    mockHttp({ audit: serverError(500, "Audit unavailable.") });
    renderPage(<AuditPage />);
    expect(await screen.findByText("Audit unavailable.")).toBeInTheDocument();
  });

  it("gives a Director no export", async () => {
    authAs(auth.useAuth, ["pms.audit_log.view"]);
    mockHttp({ audit: { ...EMPTY, results: [ENTRY] } });
    renderPage(<AuditPage />);
    expect(await screen.findByText("PMS-2026-00007")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Export CSV" })).toBeNull();
  });

  it("filters by action", async () => {
    authAs(auth.useAuth, PCC);
    const calls = mockHttp({ audit: { ...EMPTY, results: [ENTRY] } });
    renderPage(<AuditPage />);
    await userEvent.type(await screen.findByRole("textbox", { name: "Action starts with" }),
      "budget");
    await waitFor(() => expect(calls.get).toHaveBeenCalledWith("/pms/audit",
      { params: { action: "budget" } }));
  });
});
