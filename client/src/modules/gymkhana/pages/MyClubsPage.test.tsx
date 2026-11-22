import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CLUB, FAIL, PENDING, STUDENT_PERMS, grant, loaderShown, page, refusal,
  renderPage } from "../testing";
import MyClubsPage from "./MyClubsPage";

const auth = vi.hoisted(() => ({ useAuth: vi.fn() }));
vi.mock("../../../auth/AuthProvider", () => auth);

const LEADING = { "me/clubs": { leading: [CLUB], member_of: [] } };
const APPLICATION = { id: 3, club: 7, club_name: "Robotics", user_id: 1005,
  applicant_name: "Student Five (stu1005)",
  description: "I build drones", status: "open", remarks: "", approved_at: null,
  created_at: "2026-11-22" };

describe("MyClubsPage", () => {
  beforeEach(() => auth.useAuth.mockReturnValue(grant(...STUDENT_PERMS)));

  it("shows a loader while clubs load", () => {
    renderPage(<MyClubsPage />, { get: { "me/clubs": PENDING } });
    expect(loaderShown()).toBe(true);
  });

  it("tells a student who leads nothing why the page is empty", async () => {
    renderPage(<MyClubsPage />, { get: { "me/clubs": { leading: [], member_of: [] } } });
    expect(await screen.findByText("You do not lead a club")).toBeInTheDocument();
  });

  it("shows the server's message when loading fails", async () => {
    renderPage(<MyClubsPage />, { get: { "me/clubs": FAIL } });
    expect(await screen.findByText("The server is unavailable.")).toBeInTheDocument();
  });

  it("draws only the controls the role holds", async () => {
    auth.useAuth.mockReturnValue(grant("gymkhana.leadership.assign"));
    renderPage(<MyClubsPage />, { get: LEADING });
    expect(await screen.findByRole("button", { name: "Change leadership for Robotics" }))
      .toBeInTheDocument();
    expect(screen.getAllByRole("button")).toHaveLength(1);
  });

  it("approves a pending application (UC-GYM-005)", async () => {
    const { postSpy } = renderPage(<MyClubsPage />, {
      get: { ...LEADING, memberships: page([APPLICATION]) },
      post: { "memberships/approve": [{ id: 3, outcome: "approved", code: "approved",
        message: "Approved." }] } });
    await userEvent.click(await screen.findByRole("button",
      { name: "Membership requests for Robotics" }));
    await userEvent.click(await screen.findByRole("checkbox",
      { name: "Student Five (stu1005): I build drones" }));
    await userEvent.click(screen.getByRole("button", { name: "Approve selected" }));
    await waitFor(() => expect(postSpy).toHaveBeenCalledWith("/gymkhana/memberships/approve",
      { ids: [3], remarks: "" }));
    expect(await screen.findByText("Applications decided")).toBeInTheDocument();
  });

  it("shows a refusal from a budget request as sent (BR-GYM-018)", async () => {
    renderPage(<MyClubsPage />, { get: LEADING, post: { "budget-requests/create":
      refusal(422, "Only Google Drive links are accepted.") } });
    await userEvent.click(await screen.findByRole("button",
      { name: "Request budget for Robotics" }));
    await userEvent.type(await screen.findByLabelText(/purpose/i), "Parts");
    await userEvent.type(screen.getByLabelText(/amount/i), "100");
    await userEvent.type(screen.getByLabelText(/^description/i), "Motors");
    await userEvent.type(screen.getByLabelText(/supporting document/i), "https://x.test");
    await userEvent.click(screen.getByRole("button", { name: "Submit request" }));
    expect(await screen.findByText("Only Google Drive links are accepted."))
      .toBeInTheDocument();
  });
});
