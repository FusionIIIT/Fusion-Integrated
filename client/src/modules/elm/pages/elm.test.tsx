import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { http } from "../../../lib/http";
import type { Application } from "../api";
import ApplyLeavePage from "./ApplyLeavePage";
import SubstituteRequestsPage from "./SubstituteRequestsPage";
import UnitHeadReviewPage from "./UnitHeadReviewPage";
import SanctionPage from "./SanctionPage";
import MyLeavesPage from "./MyLeavesPage";

vi.mock("../../../lib/http", () => ({
  http: { get: vi.fn(), post: vi.fn() },
  errorMessage: () => "The server refused this request.",
}));

function show(page: React.ReactNode) {
  return render(<MantineProvider><MemoryRouter>{page}</MemoryRouter></MantineProvider>);
}

const row: Application = {
  id: "request-1", category: "CL", start_date: "2026-01-02", end_date: "2026-01-02",
  num_days: "0.5", remarks: "Test purpose", station_leave_details: {},
  state: "Awaiting Substitute Response", unit_head_recommendation: null,
  allowed_actions: ["substitute-response"],
};
const page = (results: Application[]) => ({ data: { count: results.length, results, next: null, previous: null } });

beforeEach(() => {
  vi.mocked(http.get).mockReset();
  vi.mocked(http.post).mockReset();
});

describe("ELM pages", () => {
  it("submits without client applicant or day count", async () => {
    vi.mocked(http.get).mockResolvedValue(page([]));
    vi.mocked(http.post).mockResolvedValue({ data: {} });
    show(<ApplyLeavePage />);
    fireEvent.change(screen.getByLabelText("Start date", { exact: false }), { target: { value: "2026-01-02" } });
    fireEvent.change(screen.getByLabelText("End date", { exact: false }), { target: { value: "2026-01-02" } });
    fireEvent.click(screen.getByRole("button", { name: "Submit application" }));
    await screen.findByText("Leave application submitted.");
    const payload = vi.mocked(http.post).mock.calls[0]?.[1];
    expect(payload).not.toHaveProperty("applicant");
    expect(payload).not.toHaveProperty("num_days");
    expect(screen.queryByLabelText("Employee ID")).not.toBeInTheDocument();
  });

  it("loads colleagues from every page", async () => {
    vi.mocked(http.get).mockResolvedValueOnce({
      data: { results: [{ id: 1, name: "First colleague" }], next: "/elm/colleagues/?page=2" },
    }).mockResolvedValueOnce({
      data: { results: [{ id: 2, name: "Second colleague" }], next: null },
    });
    show(<ApplyLeavePage />);
    await waitFor(() => expect(http.get).toHaveBeenCalledWith("/elm/colleagues/?page=2"));
  });

  it("reloads substitute tasks after acceptance", async () => {
    vi.mocked(http.get).mockResolvedValueOnce(page([row])).mockResolvedValueOnce(page([]));
    vi.mocked(http.post).mockResolvedValue({ data: {} });
    show(<SubstituteRequestsPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Accept" }));
    await screen.findByText("No requests.");
    expect(http.post).toHaveBeenCalledWith("/elm/applications/request-1/substitute-response/", { accept: true });
  });

  it("shows higher-sanction recommendations at Unit Head", async () => {
    vi.mocked(http.get).mockResolvedValue(page([{
      ...row, category: "EL", state: "Awaiting Unit Head Review",
      allowed_actions: ["unit-head-review"],
    }]));
    show(<UnitHeadReviewPage />);
    expect(await screen.findByRole("button", { name: "Not Recommended" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
  });

  it("shows Not Recommended to the final authority without blocking approve", async () => {
    vi.mocked(http.get).mockResolvedValue(page([{
      ...row, category: "EL", state: "Awaiting Final Sanction Decision",
      unit_head_recommendation: "Not Recommended", allowed_actions: ["final-decision"],
    }]));
    show(<SanctionPage />);
    expect(await screen.findByText("Unit Head: Not Recommended")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Approve" })).toBeEnabled();
  });

  it("shows days and state without mutation controls", async () => {
    vi.mocked(http.get).mockResolvedValue(page([row]));
    show(<MyLeavesPage />);
    expect(await screen.findByText("0.5 days — Awaiting Substitute Response")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Accept" })).not.toBeInTheDocument();
  });

  it("does not show actions on a visible unassigned task", async () => {
    vi.mocked(http.get).mockResolvedValue(page([{ ...row, allowed_actions: [] }]));
    show(<SubstituteRequestsPage />);
    await screen.findByText("0.5 days — Awaiting Substitute Response");
    expect(screen.queryByRole("button", { name: "Accept" })).not.toBeInTheDocument();
  });

  it("shows server errors", async () => {
    vi.mocked(http.get).mockRejectedValue(new Error("refused"));
    show(<MyLeavesPage />);
    expect(await screen.findByRole("alert")).toHaveTextContent("The server refused this request.");
  });
});
