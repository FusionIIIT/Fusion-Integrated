import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { authAs, hasLoader, mockHttp, renderPage, serverError } from "../test-utils";
import ReportsPage from "./ReportsPage";

const auth = vi.hoisted(() => ({ useAuth: vi.fn() }));
vi.mock("../../../auth/AuthProvider", () => auth);

const OFFICE = ["pms.report.view", "pms.report.export", "pms.report_definition.create"];

describe("ReportsPage", () => {
  afterEach(() => vi.restoreAllMocks());

  it("shows a spinner while loading", () => {
    authAs(auth.useAuth, OFFICE);
    mockHttp({ "reports/status": "pending", "report-definitions": [] });
    const { container } = renderPage(<ReportsPage />);
    expect(hasLoader(container)).toBe(true);
  });

  it("shows an empty state", async () => {
    authAs(auth.useAuth, OFFICE);
    mockHttp({ "reports/status": { columns: ["reference"], rows: [] }, "report-definitions": [] });
    renderPage(<ReportsPage />);
    expect(await screen.findByText("Nothing to report yet")).toBeInTheDocument();
  });

  it("shows the server's message when the report fails", async () => {
    authAs(auth.useAuth, OFFICE);
    mockHttp({ "reports/status": serverError(500, "Report unavailable."),
      "report-definitions": [] });
    renderPage(<ReportsPage />);
    expect(await screen.findByText("Report unavailable.")).toBeInTheDocument();
  });

  it("gives an applicant no export or scheduling", async () => {
    authAs(auth.useAuth, ["pms.report.view"]);
    mockHttp({ "reports/status": { columns: ["reference"], rows: [{ reference: "PMS-1" }] } });
    renderPage(<ReportsPage />);
    expect(await screen.findByText("PMS-1")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Export CSV" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Save and schedule" })).toBeNull();
  });

  it("saves a scheduled report", async () => {
    authAs(auth.useAuth, OFFICE);
    const calls = mockHttp({ "reports/status": { columns: ["reference"], rows: [] },
      "report-definitions": [] }, { "report-definitions": serverError(422, "Name the report.") });
    renderPage(<ReportsPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Save and schedule" }));
    await userEvent.type(screen.getByRole("textbox", { name: "Name" }), "Weekly");
    await userEvent.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(calls.post).toHaveBeenCalledWith("/pms/report-definitions",
      { name: "Weekly", report_type: "status", schedule: "none" }));
    expect(await screen.findByText("Name the report.")).toBeInTheDocument();
  });
});
