// DashboardPage tests covering loading, empty notifications, error, and KPI rendering.
import { screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { renderPsmPage } from "../testHelper";
import DashboardPage from "./DashboardPage";

describe("DashboardPage", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("renders loading skeletons before API responds", () => {
    vi.spyOn(http, "get").mockReturnValue(new Promise(() => undefined));
    renderPsmPage(<DashboardPage />, ["psm.dashboard.view"]);
    expect(screen.getByRole("heading", { name: /procurement & stores dashboard/i })).toBeInTheDocument();
  });

  it("renders error state on 500", async () => {
    vi.spyOn(http, "get").mockRejectedValue({ response: { status: 500, data: { error: { message: "Server failure" } } } });
    renderPsmPage(<DashboardPage />, ["psm.dashboard.view"]);
    await waitFor(() => expect(screen.getByText(/server failure/i)).toBeInTheDocument());
  });

  it("renders KPIs and empty notifications state", async () => {
    vi.spyOn(http, "get").mockImplementation(async (url: string) => {
      if (url === "/psm/dashboard") {
        return {
          data: {
            active_role: "faculty", indents_total: 4, indents_pending_approval: 2,
            indents_by_status: {}, purchase_orders_total: 1, purchase_orders_by_status: {},
            open_discrepancies: 0, pending_transfers: 0, invoices_on_hold: 0, invoices_pending_payment: 0,
          },
        };
      }
      return { data: { next: null, previous: null, results: [] } };
    });
    renderPsmPage(<DashboardPage />, ["psm.dashboard.view"]);
    await waitFor(() => expect(screen.getByText("No notifications yet.")).toBeInTheDocument());
    expect(screen.getByText("4")).toBeInTheDocument();
  });
});
