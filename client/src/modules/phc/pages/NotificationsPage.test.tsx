import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import NotificationsPage from "./NotificationsPage";
import { listStateTests, renderPage, state } from "./testing";

const http = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn() }));
vi.mock("../../../lib/http", async (orig) => ({
  ...(await orig<typeof import("../../../lib/http")>()), http,
}));
vi.mock("../../../auth/AuthProvider", () => ({
  useAuth: () => ({ can: (p: string) => state.permissions.has(p) }),
}));

const page = (rows: unknown[]) => ({ results: rows, next: null, previous: null });

describe("NotificationsPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    state.permissions = new Set(["phc.notification.view"]);
  });

  listStateTests({ get: http.get, page: () => <NotificationsPage />, empty: page([]),
    emptyText: /no notifications/i });

  it("lists the caller's notifications and offers no write control", async () => {
    http.get.mockResolvedValue({ data: page([{ id: 8, kind: "claim_status",
      message: "Your reimbursement claim #7 is now reimbursed.",
      resource_type: "reimbursement_claim", resource_id: 7,
      created_at: "2026-11-23T15:00:00Z" }]) });
    renderPage(<NotificationsPage />);
    expect(await screen.findByText("Your reimbursement claim #7 is now reimbursed."))
      .toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(http.get).toHaveBeenCalledWith("/phc/notifications", { params: undefined });
  });
});
