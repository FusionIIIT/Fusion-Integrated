/** HR-EIS page-state regressions for loading, empty, errors and successful reads. */
import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import AuditPage from "./AuditPage";
import MyRecordPage from "./MyRecordPage";
import NotificationsPage from "./NotificationsPage";
import RequestsPage from "./RequestsPage";

const hooks = vi.hoisted(() => ({
  useRequests: vi.fn(),
  useMyServiceRecord: vi.fn(),
  useNotifications: vi.fn(),
  useAuditEvents: vi.fn(),
  useComplianceRequests: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);
vi.mock("./RequestComposer", () => ({
  RequestComposer: () => <span>Employee request form</span>,
}));
vi.mock("./RequestActions", () => ({
  RequestActions: () => <span>Request actions</span>,
}));

function show(ui: React.ReactElement) {
  return render(<MantineProvider>{ui}</MantineProvider>);
}
function state(data: unknown = undefined, error: unknown = null, isPending = false) {
  return { data, error, isPending };
}

describe("HR-EIS page states", () => {
  beforeEach(() => {
    hooks.useRequests.mockReturnValue(state({ results: [] }));
    hooks.useMyServiceRecord.mockReturnValue(state());
    hooks.useNotifications.mockReturnValue(state({ results: [] }));
    hooks.useAuditEvents.mockReturnValue(state({ results: [] }));
    hooks.useComplianceRequests.mockReturnValue(state({ results: [] }));
  });

  it("shows request loading and no stale success content", () => {
    hooks.useRequests.mockReturnValue(state(undefined, null, true));
    show(<RequestsPage />);
    expect(screen.getByText("Loading request statuses...")).toBeInTheDocument();
    expect(screen.queryByText(/There are no HR requests/)).toBeNull();
  });

  it("shows scoped request empty state", () => {
    show(<RequestsPage />);
    expect(screen.getByText(/There are no HR requests in your current role/)).toBeInTheDocument();
  });

  it("shows request fetch error rather than an empty state", () => {
    hooks.useRequests.mockReturnValue(state(undefined, new Error("server down")));
    show(<RequestsPage />);
    expect(screen.getByText("Could not load this")).toBeInTheDocument();
    expect(screen.queryByText(/There are no HR requests/)).toBeNull();
  });

  it("shows a successful request and status in the scoped table", () => {
    hooks.useRequests.mockReturnValue(state({ results: [{
      id: 5, family: "leave", subtype: "Casual", state: "pending_authority",
      submitted_at: "2026-11-21T12:00:00Z",
    }] }));
    show(<RequestsPage />);
    expect(screen.getByText("#5")).toBeInTheDocument();
    expect(screen.getByText("Pending Authority")).toBeInTheDocument();
  });

  it("shows missing own service record as a specific non-sensitive state", () => {
    hooks.useMyServiceRecord.mockReturnValue(state(undefined, {
      response: { status: 404, data: { detail: "not found" } },
    }));
    show(<MyRecordPage />);
    expect(screen.getByText("No service record available")).toBeInTheDocument();
    expect(screen.queryByText("Could not load this")).toBeNull();
  });

  it("shows loading own record without granting edits", () => {
    hooks.useMyServiceRecord.mockReturnValue(state(undefined, null, true));
    show(<MyRecordPage />);
    expect(screen.getByText("Loading your service record...")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /save/i })).toBeNull();
  });

  it("shows a verified ledger-derived balance on a successful own record", () => {
    hooks.useMyServiceRecord.mockReturnValue(state({
      user_id: 10,
      department: "CSE",
      designation_snapshot: "Professor",
      retirement_status: "",
      revision: 1,
      leave_balances: { Casual: "4.5" },
      appointment_details: {},
      service_history: [],
    }));
    show(<MyRecordPage />);
    expect(screen.getByText("Verified leave balances")).toBeInTheDocument();
    expect(screen.getByText("4.5 days")).toBeInTheDocument();
    expect(screen.getByText("No service-history entries recorded.")).toBeInTheDocument();
  });

  it("does not crash when a partially deployed API omits leave balances", () => {
    hooks.useMyServiceRecord.mockReturnValue(state({
      user_id: 10,
      department: "CSE",
      designation_snapshot: "Professor",
      retirement_status: "",
      revision: 1,
      appointment_details: {},
      service_history: [],
    }));
    show(<MyRecordPage />);
    expect(screen.getByText("Verified leave balances")).toBeInTheDocument();
    expect(screen.getByText("No verified leave credits have been recorded.")).toBeInTheDocument();
  });

  it("shows notifications loading, empty and error states", () => {
    hooks.useNotifications.mockReturnValue(state(undefined, null, true));
    const page = show(<NotificationsPage />);
    expect(screen.getByText("Loading notifications...")).toBeInTheDocument();
    page.unmount();

    hooks.useNotifications.mockReturnValue(state({ results: [] }));
    const empty = show(<NotificationsPage />);
    expect(screen.getByText("No notifications yet.")).toBeInTheDocument();
    empty.unmount();

    hooks.useNotifications.mockReturnValue(state(undefined, new Error("mail unavailable")));
    show(<NotificationsPage />);
    expect(screen.getByText("Could not load this")).toBeInTheDocument();
  });

  it("renders an authorized notification without other-user information", () => {
    hooks.useNotifications.mockReturnValue(state({ results: [{
      id: 99,
      title: "HR-EIS action reminder",
      message: "An HR request awaits your assigned action.",
      created_at: "2026-11-21T12:00:00Z",
    }] }));
    show(<NotificationsPage />);
    expect(screen.getByText("HR-EIS action reminder")).toBeInTheDocument();
  });

  it("shows authorized compliance request statuses without private claim evidence", () => {
    hooks.useComplianceRequests.mockReturnValue(state({ results: [{
      id: 42,
      user_id: 10,
      family: "leave",
      state: "approved",
      created_at: "2026-11-21T10:00:00Z",
      submitted_at: "2026-11-21T10:00:00Z",
    }] }));
    show(<AuditPage />);
    expect(screen.getByText("Request compliance status")).toBeInTheDocument();
    expect(screen.getByText("#42")).toBeInTheDocument();
    expect(screen.getByText("LEAVE")).toBeInTheDocument();
    expect(screen.queryByText(/medical justification/i)).toBeNull();
  });

  it("shows audit loading, empty and error states", () => {
    hooks.useAuditEvents.mockReturnValue(state(undefined, null, true));
    const page = show(<AuditPage />);
    expect(screen.getByText("Loading audit records...")).toBeInTheDocument();
    page.unmount();

    hooks.useAuditEvents.mockReturnValue(state({ results: [] }));
    hooks.useComplianceRequests.mockReturnValue(state({ results: [] }));
    const empty = show(<AuditPage />);
    expect(screen.getByText("No audited transactions have been recorded.")).toBeInTheDocument();
    empty.unmount();

    hooks.useAuditEvents.mockReturnValue(state(undefined, new Error("unavailable")));
    show(<AuditPage />);
    expect(screen.getByText("Could not load this")).toBeInTheDocument();
  });
});
