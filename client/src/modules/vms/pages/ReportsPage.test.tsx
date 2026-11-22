import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as download from "../../../lib/download";
import { http } from "../../../lib/http";
import { renderPage, routeGet } from "../test-utils";
import ReportsPage from "./ReportsPage";

const auth = vi.hoisted(() => ({ perms: new Set<string>() }));
vi.mock("../../../auth/AuthProvider", () => ({
  useAuth: () => ({ can: (p: string) => auth.perms.has(p) }),
}));

const catalogue = [
  { key: "daily_summary", title: "Daily summary", params: ["start", "end"], identity: false },
  { key: "frequent_visitors", title: "Frequent visitors", params: ["start", "end"], identity: true },
];

beforeEach(() => { auth.perms = new Set(["vms.report.view"]); });

async function choose(title: string) {
  await userEvent.click(screen.getByPlaceholderText("Choose a report"));
  await userEvent.click(await screen.findByRole("option", { name: title }));
}

describe("ReportsPage", () => {
  it("asks for a report before showing anything", async () => {
    routeGet({ "/vms/reports": catalogue });
    renderPage(<ReportsPage />);
    expect(await screen.findByText("Choose a report to see it here.")).toBeInTheDocument();
  });

  it("runs the chosen report with the chosen dates and shows its rows", async () => {
    const get = routeGet({
      "/vms/reports": catalogue,
      "/vms/reports/daily_summary": { columns: ["date", "check_ins"], truncated: false,
        rows: [{ date: "2026-01-05", check_ins: 4 }] } });
    renderPage(<ReportsPage />);
    await screen.findByPlaceholderText("Choose a report");
    await userEvent.type(screen.getByLabelText("From"), "2026-01-01");
    await choose("Daily summary");
    expect(await screen.findByText("2026-01-05")).toBeInTheDocument();
    expect(screen.getByText("Check ins")).toBeInTheDocument();
    expect(get).toHaveBeenCalledWith("/vms/reports/daily_summary", { params: { start: "2026-01-01" } });
  });

  it("says when a report was cut short", async () => {
    routeGet({ "/vms/reports": catalogue,
      "/vms/reports/daily_summary": { columns: ["date"], truncated: true, rows: [{ date: "d" }] } });
    renderPage(<ReportsPage />);
    await screen.findByPlaceholderText("Choose a report");
    await choose("Daily summary");
    expect(await screen.findByText(/Showing the first rows only/)).toBeInTheDocument();
  });

  it("shows no download buttons without the export permission", async () => {
    routeGet({ "/vms/reports": catalogue,
      "/vms/reports/daily_summary": { columns: [], truncated: false, rows: [] } });
    renderPage(<ReportsPage />);
    await screen.findByPlaceholderText("Choose a report");
    await choose("Daily summary");
    await screen.findByText("No data for this period");
    expect(screen.queryByRole("button", { name: /download pdf/i })).not.toBeInTheDocument();
  });

  it("downloads a PDF through the export endpoint", async () => {
    auth.perms = new Set(["vms.report.view", "vms.report.export"]);
    routeGet({ "/vms/reports": catalogue,
      "/vms/reports/daily_summary": { columns: [], truncated: false, rows: [] } });
    renderPage(<ReportsPage />);
    await screen.findByPlaceholderText("Choose a report");
    await choose("Daily summary");
    vi.restoreAllMocks();
    vi.spyOn(download, "saveBlob").mockImplementation(() => undefined);
    const get = vi.spyOn(http, "get").mockResolvedValue({
      data: new Blob(["%PDF"]), headers: {
        "content-disposition": 'attachment; filename="vms-daily_summary.pdf"' } });
    await userEvent.click(await screen.findByRole("button", { name: /download pdf/i }));
    await waitFor(() => expect(get).toHaveBeenCalledWith(
      "/vms/reports/daily_summary/export", { params: { fmt: "pdf" }, responseType: "blob" }));
    expect(download.saveBlob).toHaveBeenCalled();
  });

  it("offers to show names only to someone cleared for personal data, and warns when on", async () => {
    auth.perms = new Set(["vms.report.view", "vms.report.view_pii"]);
    routeGet({ "/vms/reports": catalogue,
      "/vms/reports/frequent_visitors": { columns: [], truncated: false, rows: [] } });
    renderPage(<ReportsPage />);
    await screen.findByPlaceholderText("Choose a report");
    await choose("Frequent visitors");
    const toggle = await screen.findByLabelText(/show names and contact details/i);
    await userEvent.click(toggle);
    expect(await screen.findByText(/recorded\s+in the audit trail/)).toBeInTheDocument();
  });

  it("does not offer the names switch for a report without identities", async () => {
    auth.perms = new Set(["vms.report.view", "vms.report.view_pii"]);
    routeGet({ "/vms/reports": catalogue,
      "/vms/reports/daily_summary": { columns: [], truncated: false, rows: [] } });
    renderPage(<ReportsPage />);
    await screen.findByPlaceholderText("Choose a report");
    await choose("Daily summary");
    await screen.findByText("No data for this period");
    expect(screen.queryByLabelText(/show names/i)).not.toBeInTheDocument();
  });
});
