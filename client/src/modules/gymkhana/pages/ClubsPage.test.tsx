import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import {
  access, club, membership, mockHttp, page, pending, refusal, show,
} from "../test/harness";
import ClubsPage from "./ClubsPage";

const MAY_APPLY = access(["gymkhana.club.view", "gymkhana.membership.create"]);
const gets = (over = {}) => ({
  "/gymkhana/access/": MAY_APPLY, "/gymkhana/clubs/": page(club),
  "/gymkhana/memberships/": page(), ...over,
});

describe("ClubsPage", () => {
  it("shows a loading state", () => {
    mockHttp(gets({ "/gymkhana/clubs/": pending }));
    show(<ClubsPage />);
    expect(screen.queryByText("Robotics Club")).not.toBeInTheDocument();
    expect(screen.queryByText("No clubs yet")).not.toBeInTheDocument();
  });

  it("shows an empty state", async () => {
    mockHttp(gets({ "/gymkhana/clubs/": page() }));
    show(<ClubsPage />);
    expect(await screen.findByText("No clubs yet")).toBeInTheDocument();
  });

  it("shows the server's error, not a spinner", async () => {
    mockHttp(gets({ "/gymkhana/clubs/": refusal(500, "Database is down") }));
    show(<ClubsPage />);
    expect(await screen.findByText("Database is down")).toBeInTheDocument();
  });

  it("offers no Apply button to a role that may not apply, and never asks for memberships", async () => {
    mockHttp({ "/gymkhana/access/": access(["gymkhana.club.view"]),
      "/gymkhana/clubs/": page(club) });
    show(<ClubsPage />);
    expect(await screen.findByText("Robotics Club")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /apply/i })).not.toBeInTheDocument();
  });

  it("offers no second application", async () => {
    mockHttp(gets({ "/gymkhana/memberships/": page(membership) }));
    show(<ClubsPage />);
    expect(await screen.findByText("Applied")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /apply to/i })).not.toBeInTheDocument();
  });

  it("submits an application", async () => {
    const post = mockHttp(gets(), { "/gymkhana/memberships/apply/": membership });
    show(<ClubsPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Apply to Robotics Club" }));
    await userEvent.type(screen.getByLabelText(/achievements/i), "I build robots");
    await userEvent.click(screen.getByRole("button", { name: "Submit application" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/gymkhana/memberships/apply/",
      { club_id: 1, description: "I build robots" }));
    expect(await screen.findByText("Application submitted")).toBeInTheDocument();
  });

  it("shows a refusal as the server sent it", async () => {
    mockHttp(gets(), { "/gymkhana/memberships/apply/": refusal(409, "You have already applied.") });
    show(<ClubsPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Apply to Robotics Club" }));
    await userEvent.type(screen.getByLabelText(/achievements/i), "Again");
    await userEvent.click(screen.getByRole("button", { name: "Submit application" }));
    expect(await screen.findByText("You have already applied.")).toBeInTheDocument();
  });
});
