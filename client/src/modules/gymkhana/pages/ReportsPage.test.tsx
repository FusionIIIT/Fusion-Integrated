import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { FAIL, PENDING, loaderShown, page, refusal, renderPage } from "../testing";
import ReportsPage from "./ReportsPage";

const REPORT = { id: 5, club: 7, club_name: "Robotics", student_incharge_user_id: 1001,
  student_incharge_name: "Student One (stu1001)",
  event_name: "RoboWars", event_at: "2026-11-20T10:30:00Z", description: "Went well",
  report_link: "https://drive.google.com/file/d/1AbCdEfGhIjK/view",
  submitted_by_user_id: 1001, created_at: "2026-11-22" };

describe("ReportsPage", () => {
  it("shows a loader while reports load", () => {
    renderPage(<ReportsPage />, { get: { "event-reports": PENDING } });
    expect(loaderShown()).toBe(true);
  });

  it("explains an empty list", async () => {
    renderPage(<ReportsPage />, { get: { "event-reports": page([]) } });
    expect(await screen.findByText("No reports to review")).toBeInTheDocument();
  });

  it("shows the server's message when loading fails", async () => {
    renderPage(<ReportsPage />, { get: { "event-reports": FAIL } });
    expect(await screen.findByText("The server is unavailable.")).toBeInTheDocument();
  });

  it("has no write control at all: review is read-only (UC-GYM-012)", async () => {
    renderPage(<ReportsPage />, { get: { "event-reports": page([REPORT]) } });
    expect(await screen.findByText("RoboWars")).toBeInTheDocument();
    const buttons = screen.getAllByRole("button").map((b) => b.textContent);
    expect(buttons).toEqual(["Review"]);
  });

  it("opens a report with its file link", async () => {
    renderPage(<ReportsPage />, { get: { "event-reports": page([REPORT]),
      "event-reports/5": REPORT } });
    await userEvent.click(await screen.findByRole("button", { name: "Review RoboWars" }));
    expect(await screen.findByRole("link", { name: "Open the report file" }))
      .toHaveAttribute("href", REPORT.report_link);
  });

  it("shows a refused detail as sent (BR-GYM-021)", async () => {
    renderPage(<ReportsPage />, { get: { "event-reports": page([REPORT]),
      "event-reports/5": refusal(404, "Not found.") } });
    await userEvent.click(await screen.findByRole("button", { name: "Review RoboWars" }));
    expect(await screen.findByText("Not found.")).toBeInTheDocument();
  });
});
