import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { membership, mockHttp, page, pending, refusal, show } from "../test/harness";
import MembershipsPage from "./MembershipsPage";

const PATH = "/gymkhana/memberships/";

describe("MembershipsPage", () => {
  it("shows a loading state", () => {
    mockHttp({ [PATH]: pending });
    show(<MembershipsPage />);
    expect(screen.queryByText("No applications yet")).not.toBeInTheDocument();
  });

  it("shows an empty state", async () => {
    mockHttp({ [PATH]: page() });
    show(<MembershipsPage />);
    expect(await screen.findByText("No applications yet")).toBeInTheDocument();
  });

  it("shows the server's error", async () => {
    mockHttp({ [PATH]: refusal(500, "Database is down") });
    show(<MembershipsPage />);
    expect(await screen.findByText("Database is down")).toBeInTheDocument();
  });

  it("says plainly when the acting role has no memberships page", async () => {
    mockHttp({ [PATH]: refusal(403, "no") });
    show(<MembershipsPage />);
    expect(await screen.findByText("Not available to your role")).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("shows each application, its status and its remarks", async () => {
    mockHttp({ [PATH]: page({ ...membership, status: "confirmed", remarks: "Welcome" }) });
    show(<MembershipsPage />);
    expect(await screen.findByText("Robotics Club")).toBeInTheDocument();
    expect(screen.getByText("confirmed")).toBeInTheDocument();
    expect(screen.getByText("Welcome")).toBeInTheDocument();
  });

  it("loads the next page on request", async () => {
    let call = 0;
    mockHttp({ [PATH]: () => (call++ === 0
      ? { next: "http://x/?cursor=abc", previous: null, results: [membership] }
      : page({ ...membership, id: 8, club_name: "Music Club" })) });
    show(<MembershipsPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Load more" }));
    expect(await screen.findByText("Music Club")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Load more" })).not.toBeInTheDocument();
  });
});
