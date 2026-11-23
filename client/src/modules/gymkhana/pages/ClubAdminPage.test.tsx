import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { access, choose, club, mockHttp, page, pending, refusal, show } from "../test/harness";
import ClubAdminPage from "./ClubAdminPage";

const open = { ...club, status: "open" };
const ADMIN = access(["gymkhana.club.view", "gymkhana.club.create", "gymkhana.club.approve"]);
const gets = (over = {}) => ({
  "/gymkhana/access/": ADMIN, "/gymkhana/clubs/": page(open), ...over,
});

describe("ClubAdminPage", () => {
  it("shows a loading state", () => {
    mockHttp(gets({ "/gymkhana/clubs/": pending }));
    show(<ClubAdminPage />);
    expect(screen.queryByText("No clubs yet")).not.toBeInTheDocument();
  });

  it("shows an empty state", async () => {
    mockHttp(gets({ "/gymkhana/clubs/": page() }));
    show(<ClubAdminPage />);
    expect(await screen.findByText("No clubs yet")).toBeInTheDocument();
  });

  it("shows the server's error", async () => {
    mockHttp(gets({ "/gymkhana/clubs/": refusal(500, "Database is down") }));
    show(<ClubAdminPage />);
    expect(await screen.findByText("Database is down")).toBeInTheDocument();
  });

  it("offers neither create nor review without the permissions", async () => {
    mockHttp(gets({ "/gymkhana/access/": access(["gymkhana.club.view"]) }));
    show(<ClubAdminPage />);
    expect(await screen.findByText("Robotics Club")).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("reviews then approves an open club", async () => {
    const post = mockHttp(gets(), { "/gymkhana/clubs/1/confirm/": club });
    show(<ClubAdminPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Review Robotics Club" }));
    expect(screen.getByText("Dr Rao")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Approve club" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/gymkhana/clubs/1/confirm/", {}));
    expect(await screen.findByText("Club approved")).toBeInTheDocument();
  });

  it("shows a refused approval as the server sent it", async () => {
    mockHttp(gets(), { "/gymkhana/clubs/1/confirm/": refusal(409, "Already confirmed.") });
    show(<ClubAdminPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Review Robotics Club" }));
    await userEvent.click(screen.getByRole("button", { name: "Approve club" }));
    expect(await screen.findByText("Already confirmed.")).toBeInTheDocument();
  });

  it("creates a club from searched people", async () => {
    const people = (kind: string) => () => ({ results: [
      { user_id: kind === "student" ? 101 : 201, username: "u", display_name: "Person" }] });
    const post = mockHttp(
      gets({ "/gymkhana/people/": people("student") }), { "/gymkhana/clubs/": club });
    show(<ClubAdminPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Create club" }));
    const submit = screen.getByRole("button", { name: "Create" });
    expect(submit).toBeDisabled();
    await userEvent.type(screen.getByRole("textbox", { name: /club name/i }), "Chess Club");
    await choose(/category/i, "Sports");
    for (const label of [/^coordinator/i, /^co-coordinator/i, /faculty councillor/i]) {
      await choose(label, "Person (u)", "per");
    }
    await userEvent.click(submit);
    await waitFor(() => expect(post).toHaveBeenCalledWith("/gymkhana/clubs/", {
      name: "Chess Club", description: "", category: "sports", coordinator_id: 101,
      co_coordinator_id: 101, faculty_councillor_id: 101,
    }));
  });
});
