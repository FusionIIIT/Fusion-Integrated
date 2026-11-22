import { access, boundary, claim, record, resetBoundary, show, unavailable } from "./testSupport";
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import AuditPage from "./AuditPage";
import MyRecordPage from "./MyRecordPage";
import NotificationsPage from "./NotificationsPage";
import RequestsPage from "./RequestsPage";

describe("HR pages through the shared HTTP boundary", () => {
  beforeEach(resetBoundary);
  for (const scenario of [
    { name: "requests", page: <RequestsPage />, url: "/hreis/requests/", loading: "Loading request statuses...", empty: /There are no HR requests/ },
    { name: "notifications", page: <NotificationsPage />, url: "/hreis/notifications/", loading: "Loading notifications...", empty: "No notifications yet." },
    { name: "audit", page: <AuditPage />, url: "/hreis/audit/", loading: "Loading audit records...", empty: "No audited transactions have been recorded." },
  ]) {
    it(`${scenario.name} distinguishes loading, empty and server errors`, async () => {
      boundary.get.mockImplementation(() => new Promise(() => {}));
      const loading = show(scenario.page);
      expect(screen.getByText(scenario.loading)).toBeInTheDocument();
      expect(screen.queryByText(scenario.empty)).toBeNull();
      loading.unmount();
      boundary.get.mockResolvedValue({ data: { results: [] } });
      const empty = show(scenario.page);
      expect(await screen.findByText(scenario.empty)).toBeInTheDocument();
      expect(boundary.get).toHaveBeenCalledWith(scenario.url);
      empty.unmount();
      boundary.get.mockImplementation((url: string) => url === scenario.url
        ? Promise.reject(unavailable) : Promise.resolve({ data: { results: [] } }));
      show(scenario.page);
      expect(await screen.findByText("Synthetic service unavailable. Retry shortly.")).toBeInTheDocument();
      expect(screen.queryByText(scenario.empty)).toBeNull();
    });
  }
  it("loads a scoped request and hides unauthorized workflow controls", async () => {
    boundary.get.mockResolvedValue({ data: { results: [claim] } });
    show(<RequestsPage />);
    expect(await screen.findByText("#42")).toBeInTheDocument();
    expect(screen.getByText("Approved")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Record finance status" })).toBeNull();
    expect(screen.queryByRole("button", { name: /Submit/ })).toBeNull();
  });
  it("submits leave and refreshes the real request query", async () => {
    access.permissions = ["hreis.leave.create"];
    let submitted = false;
    boundary.get.mockImplementation(() => Promise.resolve({ data: { results: submitted
      ? [{ ...claim, id: 71, family: "leave", state: "pending_authority", claim_summary: null }] : [] } }));
    boundary.post.mockImplementation(() => { submitted = true; return Promise.resolve({ data: {} }); });
    show(<RequestsPage view="leave" />);
    fireEvent.click(screen.getByRole("button", { name: "Apply for leave" }));
    fireEvent.change(await screen.findByRole("textbox", { name: "Duration (days)" }), { target: { value: "1" } });
    fireEvent.change(screen.getByRole("textbox", { name: "Justification" }), { target: { value: "Synthetic request" } });
    fireEvent.click(screen.getByRole("button", { name: "Submit request" }));
    expect(await screen.findByText("#71")).toBeInTheDocument();
    expect(boundary.post).toHaveBeenCalledWith("/hreis/requests/leave/", {
      leave_type: "Casual", duration: "1", justification: "Synthetic request",
    }, { headers: { "Idempotency-Key": expect.any(String) } });
  });
  it("shows the own-record loading, missing, error and verified balance states", async () => {
    boundary.get.mockImplementation(() => new Promise(() => {}));
    const loading = show(<MyRecordPage />);
    expect(screen.getByText("Loading your service record...")).toBeInTheDocument();
    loading.unmount();
    boundary.get.mockRejectedValue({ response: { status: 404 } });
    const missing = show(<MyRecordPage />);
    expect(await screen.findByText("No service record available")).toBeInTheDocument();
    missing.unmount();
    boundary.get.mockRejectedValue(unavailable);
    const failure = show(<MyRecordPage />);
    expect(await screen.findByText("Synthetic service unavailable. Retry shortly.")).toBeInTheDocument();
    failure.unmount();
    boundary.get.mockResolvedValue({ data: record });
    show(<MyRecordPage />);
    expect(await screen.findByText("4.5 days")).toBeInTheDocument();
    expect(boundary.get).toHaveBeenCalledWith("/hreis/service-records/me/");
    expect(screen.queryByRole("button", { name: /save|edit/i })).toBeNull();
  });
  it("marks a notification read and refetches its actual query", async () => {
    access.permissions = ["hreis.notification.view"];
    let read = false;
    boundary.get.mockImplementation(() => Promise.resolve({ data: { results: [{
      id: 9, title: "Synthetic reminder", message: "Assigned action due", created_at: "2026-11-21T00:00:00Z",
      read_at: read ? "2026-11-22T00:00:00Z" : null,
    }] } }));
    boundary.post.mockImplementation(() => { read = true; return Promise.resolve({ data: {} }); });
    show(<NotificationsPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Mark as read" }));
    expect(await screen.findByText("Read")).toBeInTheDocument();
    expect(boundary.post).toHaveBeenCalledWith("/hreis/notifications/9/read/", {}, {
      headers: { "Idempotency-Key": expect.any(String) },
    });
    expect(boundary.get.mock.calls.length).toBeGreaterThan(1);
  });
  it("keeps a rejected notification write visible and shows the server message", async () => {
    access.permissions = ["hreis.notification.view"];
    boundary.get.mockResolvedValue({ data: { results: [{ id: 9, title: "Synthetic reminder", message: "Due",
      created_at: "2026-11-21T00:00:00Z", read_at: null }] } });
    boundary.post.mockRejectedValue(unavailable);
    show(<NotificationsPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Mark as read" }));
    expect(await screen.findByText("Synthetic service unavailable. Retry shortly.")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole("button", { name: "Mark as read" })).not.toBeDisabled());
  });
  it("reads the compliance projection without rendering private evidence", async () => {
    boundary.get.mockImplementation((url: string) => Promise.resolve({ data: { results: url.includes("compliance")
      ? [{ id: 42, user_id: 10, family: "leave", state: "approved", submitted_at: "2026-11-21T00:00:00Z" }] : [] } }));
    show(<AuditPage />);
    expect(await screen.findByText("#42")).toBeInTheDocument();
    expect(screen.getByText("LEAVE")).toBeInTheDocument();
    expect(screen.queryByText(/medical justification/i)).toBeNull();
  });
});
