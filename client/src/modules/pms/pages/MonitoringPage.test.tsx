import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { authAs, hasLoader, mockHttp, renderPage, serverError } from "../test-utils";
import MonitoringPage from "./MonitoringPage";

const auth = vi.hoisted(() => ({ useAuth: vi.fn() }));
vi.mock("../../../auth/AuthProvider", () => auth);

const PERMS = ["pms.escalation.review"];
const CASE = { id: 2, kind: "missed_review", application_id: 7,
  application_reference: "PMS-2026-00007", subject_id: 11, deadline: "2026-11-20",
  status: "open", note: "", handled_at: null, created_at: "2026-11-21" };

describe("MonitoringPage", () => {
  afterEach(() => vi.restoreAllMocks());

  it("shows a spinner while loading", () => {
    authAs(auth.useAuth, PERMS);
    mockHttp({ deadlines: "pending", escalations: "pending" });
    const { container } = renderPage(<MonitoringPage />);
    expect(hasLoader(container)).toBe(true);
  });

  it("shows empty states", async () => {
    authAs(auth.useAuth, PERMS);
    mockHttp({ deadlines: [], escalations: [] });
    renderPage(<MonitoringPage />);
    expect(await screen.findByText("No open escalations")).toBeInTheDocument();
    expect(await screen.findByText("No tracked deadlines")).toBeInTheDocument();
  });

  it("shows the server's message when loading fails", async () => {
    authAs(auth.useAuth, PERMS);
    mockHttp({ deadlines: serverError(500, "Deadlines unavailable."), escalations: [] });
    renderPage(<MonitoringPage />);
    expect(await screen.findByText("Deadlines unavailable.")).toBeInTheDocument();
  });

  it("lists a missed deadline", async () => {
    authAs(auth.useAuth, PERMS);
    mockHttp({ deadlines: [{ kind: "review", subject_id: 1, application_id: 7,
      reference: "PMS-2026-00007", due_on: "2026-11-20", responsible: "Dr Rao",
      missed: true }], escalations: [] });
    renderPage(<MonitoringPage />);
    expect(await screen.findByText("Dr Rao")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Handle" })).toBeNull();
  });

  it("records how an escalation was handled", async () => {
    authAs(auth.useAuth, PERMS);
    const calls = mockHttp({ deadlines: [], escalations: [CASE] },
      { "escalations/2/handle": serverError(409, "This escalation is already resolved.") });
    renderPage(<MonitoringPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Handle" }));
    await userEvent.click(screen.getByRole("textbox", { name: "What was done" }));
    await userEvent.click(await screen.findByRole("option", { name: "Resolved", hidden: true }));
    await userEvent.type(screen.getByRole("textbox", { name: "Note" }), "Reassigned.");
    await userEvent.click(screen.getByRole("button", { name: "Record" }));
    await waitFor(() => expect(calls.post).toHaveBeenCalledWith("/pms/escalations/2/handle",
      { action: "resolve", note: "Reassigned." }));
    expect(await screen.findByText("This escalation is already resolved.")).toBeInTheDocument();
  });
});
