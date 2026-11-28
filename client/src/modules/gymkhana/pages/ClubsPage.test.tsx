import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CLUB, FAIL, PENDING, STUDENT_PERMS, grant, loaderShown, page, refusal,
  renderPage } from "../testing";
import ClubsPage from "./ClubsPage";

const auth = vi.hoisted(() => ({ useAuth: vi.fn() }));
vi.mock("../../../auth/AuthProvider", () => auth);

describe("ClubsPage", () => {
  beforeEach(() => auth.useAuth.mockReturnValue(grant(...STUDENT_PERMS)));

  it("shows a loader while clubs load", () => {
    renderPage(<ClubsPage />, { get: { clubs: PENDING } });
    expect(loaderShown()).toBe(true);
  });

  it("explains an empty list", async () => {
    renderPage(<ClubsPage />, { get: { clubs: page([]) } });
    expect(await screen.findByText("No clubs yet")).toBeInTheDocument();
  });

  it("shows the server's message when loading fails", async () => {
    renderPage(<ClubsPage />, { get: { clubs: FAIL } });
    expect(await screen.findByText("The server is unavailable.")).toBeInTheDocument();
  });

  it("offers no Apply to a role without membership.create", async () => {
    auth.useAuth.mockReturnValue(grant("gymkhana.club.view"));
    renderPage(<ClubsPage />, { get: { clubs: page([CLUB]) } });
    expect(await screen.findByText("Robotics")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /apply/i })).not.toBeInTheDocument();
  });

  it("sends an application (UC-GYM-004)", async () => {
    const { postSpy } = renderPage(<ClubsPage />, {
      get: { clubs: page([CLUB]) },
      post: { "memberships/apply": { id: 1, status: "open" } } });
    await userEvent.click(await screen.findByRole("button", { name: "Apply to Robotics" }));
    await userEvent.type(await screen.findByLabelText(/why you want to join/i), "I build drones");
    await userEvent.click(screen.getByRole("button", { name: "Send application" }));
    await waitFor(() => expect(postSpy).toHaveBeenCalledWith("/gymkhana/memberships/apply",
      { club_id: 7, description: "I build drones" }));
    expect(await screen.findByText("Application sent")).toBeInTheDocument();
  });

  it("shows a refusal as the server sent it", async () => {
    renderPage(<ClubsPage />, {
      get: { clubs: page([CLUB]) },
      post: { "memberships/apply": refusal(409, "You have already applied to this club.") } });
    await userEvent.click(await screen.findByRole("button", { name: "Apply to Robotics" }));
    await userEvent.type(await screen.findByLabelText(/why you want to join/i), "again");
    await userEvent.click(screen.getByRole("button", { name: "Send application" }));
    const dialog = await screen.findByRole("dialog");
    expect(await within(dialog).findByText("You have already applied to this club."))
      .toBeInTheDocument();
  });
});
