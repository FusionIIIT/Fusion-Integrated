import { fireEvent, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ReportsPage from "./ReportsPage";
import { refusal, renderPage, serverError, state } from "./testing";

const http = vi.hoisted(() => ({ get: vi.fn(), post: vi.fn(), put: vi.fn() }));
vi.mock("../../../lib/http", async (orig) => ({
  ...(await orig<typeof import("../../../lib/http")>()), http,
}));
vi.mock("../../../auth/AuthProvider", () => ({
  useAuth: () => ({ can: (p: string) => state.permissions.has(p) }),
}));

function generate() {
  fireEvent.change(screen.getByLabelText(/^from/i), { target: { value: "2026-11-01" } });
  fireEvent.change(screen.getByLabelText(/^to/i), { target: { value: "2026-11-30" } });
  fireEvent.click(screen.getByRole("button", { name: /generate/i }));
}

describe("ReportsPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    state.permissions = new Set(["phc.report.view"]);
  });

  it("starts empty, asking for parameters, with Generate disabled", () => {
    renderPage(<ReportsPage />);
    expect(screen.getByText(/choose a report and a date range/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /generate/i })).toBeDisabled();
    expect(http.get).not.toHaveBeenCalled();
  });

  it("shows a loading state", () => {
    http.get.mockReturnValue(new Promise(() => undefined));
    renderPage(<ReportsPage />);
    generate();
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("shows the server's message when the API fails", async () => {
    http.get.mockRejectedValue(serverError());
    renderPage(<ReportsPage />);
    generate();
    expect(await screen.findByText("The server could not answer.")).toBeInTheDocument();
  });

  it("shows an invalid-parameter refusal as sent", async () => {
    http.get.mockRejectedValue(refusal("The start date must be on or before the end date.",
      400));
    renderPage(<ReportsPage />);
    generate();
    expect(await screen.findByText("The start date must be on or before the end date."))
      .toBeInTheDocument();
  });

  it("generates the anonymised report", async () => {
    http.get.mockResolvedValue({ data: { category: "utilization", start: "2026-11-01",
      end: "2026-11-30", data: { visits_by_month: [{ month: "2026-11", visits: "<5" }] } } });
    renderPage(<ReportsPage />);
    generate();
    expect(await screen.findByText(/service utilization: 2026-11-01 to 2026-11-30/i))
      .toBeInTheDocument();
    expect(http.get).toHaveBeenCalledWith("/phc/reports", { params: {
      category: "utilization", start: "2026-11-01", end: "2026-11-30" } });
  });
});
