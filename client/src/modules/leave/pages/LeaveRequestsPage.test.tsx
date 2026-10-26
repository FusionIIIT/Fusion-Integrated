import { MantineProvider } from "@mantine/core";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import type { LeaveRequest } from "../api";
import LeaveRequestsPage from "./LeaveRequestsPage";

const request: LeaveRequest = {
  id: 41,
  leave_type: 1,
  leave_type_name: "Annual",
  start_date: "2026-11-02",
  end_date: "2026-11-02",
  days: 1,
  reason: "Personal day",
  user_id: 1001,
  employee_name: "Asha Verma",
  status: "pending",
  review_note: "",
  created_at: "2026-10-26T10:00:00Z",
};

function renderPage() {
  return render(<MantineProvider><LeaveRequestsPage /></MantineProvider>);
}

describe("LeaveRequestsPage", () => {
  beforeEach(() => {
    vi.spyOn(http, "get").mockResolvedValue({ data: { results: [request] } });
  });

  it("shows the employee name and refreshes after approval", async () => {
    const user = userEvent.setup();
    vi.spyOn(http, "post").mockResolvedValue({ data: {} });

    renderPage();

    expect(await screen.findByText("Asha Verma")).toBeInTheDocument();
    expect(screen.queryByText("1001")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Approve" }));

    await waitFor(() => expect(http.post).toHaveBeenCalledWith(
      "/leave/requests/41/review", { decision: "approved" }));
    await waitFor(() => expect(http.get).toHaveBeenCalledTimes(2));
  });

  it("uses the employee id fallback when directory data is unavailable", async () => {
    vi.spyOn(http, "get").mockResolvedValue({
      data: { results: [{ ...request, employee_name: "" }] },
    });

    renderPage();

    expect(await screen.findByText("Employee #1001")).toBeInTheDocument();
  });

  it("does not offer decisions for a completed request", async () => {
    vi.spyOn(http, "get").mockResolvedValue({
      data: { results: [{ ...request, status: "approved" }] },
    });

    renderPage();

    expect(await screen.findByText("Asha Verma")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reject" })).not.toBeInTheDocument();
  });
});
