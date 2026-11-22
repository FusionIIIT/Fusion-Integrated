import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { FAIL, PENDING, STUDENT_PERMS, grant, loaderShown, page, refusal,
  renderPage } from "../testing";
import PollsPage from "./PollsPage";

const auth = vi.hoisted(() => ({ useAuth: vi.fn() }));
vi.mock("../../../auth/AuthProvider", () => auth);

const POLL = { id: 4, club: 7, club_name: "Robotics", title: "Next workshop",
  description: "Pick one", expires_on: "2026-12-10", created_at: "2026-11-22",
  choices: [{ id: 1, label: "Drones" }, { id: 2, label: "ROS" }], my_choice_id: null };

describe("PollsPage", () => {
  beforeEach(() => auth.useAuth.mockReturnValue(grant(...STUDENT_PERMS)));

  it("shows a loader while polls load", () => {
    renderPage(<PollsPage />, { get: { polls: PENDING } });
    expect(loaderShown()).toBe(true);
  });

  it("explains an empty list", async () => {
    renderPage(<PollsPage />, { get: { polls: page([]) } });
    expect(await screen.findByText("No open polls for you")).toBeInTheDocument();
  });

  it("shows the server's message when loading fails", async () => {
    renderPage(<PollsPage />, { get: { polls: FAIL } });
    expect(await screen.findByText("The server is unavailable.")).toBeInTheDocument();
  });

  it("offers no Vote without vote.create", async () => {
    auth.useAuth.mockReturnValue(grant("gymkhana.poll.view"));
    renderPage(<PollsPage />, { get: { polls: page([POLL]) } });
    expect(await screen.findByText("Next workshop")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Vote" })).not.toBeInTheDocument();
  });

  it("casts one vote (UC-GYM-007)", async () => {
    const { postSpy } = renderPage(<PollsPage />, {
      get: { polls: page([POLL]) }, post: { "polls/4/votes": { choice_id: 2 } } });
    await userEvent.click(await screen.findByRole("radio", { name: "ROS" }));
    await userEvent.click(screen.getByRole("button", { name: "Vote" }));
    await waitFor(() => expect(postSpy).toHaveBeenCalledWith("/gymkhana/polls/4/votes",
      { choice_id: 2 }));
    expect(await screen.findByText("Vote recorded")).toBeInTheDocument();
  });

  it("shows a refusal as sent, and a cast vote instead of the form", async () => {
    renderPage(<PollsPage />, { get: { polls: page([POLL, { ...POLL, id: 5,
      title: "Done", my_choice_id: 1 }]) },
    post: { "polls/4/votes": refusal(409, "This poll has closed.") } });
    expect(await screen.findByText("Drones", { selector: "b" })).toBeInTheDocument();
    await userEvent.click(await screen.findByRole("radio", { name: "ROS" }));
    await userEvent.click(screen.getByRole("button", { name: "Vote" }));
    expect(await screen.findByText("This poll has closed.")).toBeInTheDocument();
  });
});
