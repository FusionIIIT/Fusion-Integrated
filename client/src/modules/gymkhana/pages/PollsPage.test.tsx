import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { access, mockHttp, page, pending, poll, refusal, show } from "../test/harness";
import PollsPage from "./PollsPage";

const gets = (over = {}) => ({
  "/gymkhana/access/": access(["gymkhana.poll.view", "gymkhana.poll.vote"]),
  "/gymkhana/polls/": page(poll), ...over,
});

describe("PollsPage", () => {
  it("shows a loading state", () => {
    mockHttp(gets({ "/gymkhana/polls/": pending }));
    show(<PollsPage />);
    expect(screen.getByLabelText("Loading polls")).toBeInTheDocument();
  });

  it("shows an empty state", async () => {
    mockHttp(gets({ "/gymkhana/polls/": page() }));
    show(<PollsPage />);
    expect(await screen.findByText("No open polls for you right now.")).toBeInTheDocument();
  });

  it("does not offer a poll that has closed", async () => {
    mockHttp(gets({ "/gymkhana/polls/": page({ ...poll, expires_at: "2020-01-01T00:00:00Z" }) }));
    show(<PollsPage />);
    expect(await screen.findByText("No open polls for you right now.")).toBeInTheDocument();
  });

  it("shows the server's error", async () => {
    mockHttp(gets({ "/gymkhana/polls/": refusal(500, "Database is down") }));
    show(<PollsPage />);
    expect(await screen.findByText("Database is down")).toBeInTheDocument();
  });

  it("offers no vote without the permission", async () => {
    mockHttp(gets({ "/gymkhana/access/": access(["gymkhana.poll.view"]) }));
    show(<PollsPage />);
    expect(await screen.findByText("Next workshop")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Vote" })).not.toBeInTheDocument();
    expect(screen.queryByRole("radio")).not.toBeInTheDocument();
  });

  it("records one vote", async () => {
    const post = mockHttp(gets(), { "/gymkhana/polls/5/vote/": { ...poll, has_voted: true } });
    show(<PollsPage />);
    expect(await screen.findByRole("button", { name: "Vote" })).toBeDisabled();
    await userEvent.click(screen.getByRole("radio", { name: "ROS" }));
    await userEvent.click(screen.getByRole("button", { name: "Vote" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith(
      "/gymkhana/polls/5/vote/", { choice_id: 52 }));
    expect(await screen.findByText("Vote recorded")).toBeInTheDocument();
  });

  it("shows the tally instead of the choices once voted", async () => {
    mockHttp(gets({ "/gymkhana/polls/": page({ ...poll, has_voted: true }) }));
    show(<PollsPage />);
    expect(await screen.findByText("3 of 4")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Vote" })).not.toBeInTheDocument();
  });

  it("shows a refusal as the server sent it", async () => {
    mockHttp(gets(), { "/gymkhana/polls/5/vote/": refusal(409, "You have already cast a vote.") });
    show(<PollsPage />);
    await userEvent.click(await screen.findByRole("radio", { name: "ROS" }));
    await userEvent.click(screen.getByRole("button", { name: "Vote" }));
    expect(await screen.findByText("You have already cast a vote.")).toBeInTheDocument();
  });
});
