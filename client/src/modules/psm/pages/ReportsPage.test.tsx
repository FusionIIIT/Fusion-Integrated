// ReportsPage tests: loading, empty, error, permission gate, and report generation.
import { fireEvent, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { renderPsmPage } from "../testHelper";
import ReportsPage from "./ReportsPage";

describe("ReportsPage", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("renders loading state", () => {
    vi.spyOn(http, "get").mockReturnValue(new Promise(() => undefined));
    renderPsmPage(<ReportsPage />, ["psm.report.view"]);
    expect(screen.getByRole("heading", { name: /reports & schedules/i })).toBeInTheDocument();
  });

  it("renders empty schedules and hides export/schedule buttons without permission", async () => {
    vi.spyOn(http, "get").mockResolvedValue({ data: { results: [] } });
    renderPsmPage(<ReportsPage />, ["psm.report.view"]);
    await waitFor(() => expect(screen.getByText(/no scheduled reports configured/i)).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: /export csv/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /schedule report/i })).not.toBeInTheDocument();
  });

  it("renders error state on 500", async () => {
    vi.spyOn(http, "get").mockRejectedValue({ response: { status: 500, data: { error: { message: "Reports error" } } } });
    renderPsmPage(<ReportsPage />, ["psm.report.view"]);
    await waitFor(() => expect(screen.getByText(/reports error/i)).toBeInTheDocument());
  });

  it("generates a report and displays the logged result", async () => {
    vi.spyOn(http, "get").mockImplementation(async (url: string) => {
      if (url.includes("/reports/logs")) {
        return {
          data: {
            results: [
              {
                id: 9,
                report_type: "operational",
                trigger_type: "scheduled",
                schedule_id: 2,
                schedule_name: "Weekly Ops",
                export_format: "json",
                row_count: 5,
                status: "succeeded",
                error_message: "",
                created_at: "2026-11-23T10:00:00Z",
              },
            ],
          },
        };
      }
      return {
        data: {
          results: [
            {
              id: 2,
              name: "Weekly Ops",
              report_type: "operational",
              filters: {},
              cadence: "weekly",
              is_active: true,
              last_run_at: null,
              next_run_at: "2026-11-30T10:00:00Z",
            },
          ],
        },
      };
    });
    vi.spyOn(http, "post").mockResolvedValue({
      data: { log_id: 7, report_type: "operational", headers: [], rows: [], row_count: 3 },
    });
    renderPsmPage(<ReportsPage />, ["psm.report.view", "psm.report.export", "psm.report.create"]);
    fireEvent.click(screen.getByRole("button", { name: /generate report/i }));
    await waitFor(() => expect(screen.getByText(/log #7.*3 row/i)).toBeInTheDocument());
    await waitFor(() => expect(screen.getByText("Report Generation Logs")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: /run now/i })).toBeInTheDocument();
  });
});
