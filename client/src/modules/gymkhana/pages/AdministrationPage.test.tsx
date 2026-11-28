import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CLUB, FAIL, PENDING, grant, loaderShown, page, refusal,
  renderPage } from "../testing";
import AdministrationPage from "./AdministrationPage";

const auth = vi.hoisted(() => ({ useAuth: vi.fn() }));
vi.mock("../../../auth/AuthProvider", () => auth);

const OPEN = { ...CLUB, id: 8, name: "Chess", status: "open", approved_at: null };
const ADMIN = ["gymkhana.club.view", "gymkhana.club.create", "gymkhana.club.approve"];

describe("AdministrationPage", () => {
  beforeEach(() => auth.useAuth.mockReturnValue(grant(...ADMIN)));

  it("shows a loader while clubs load", () => {
    renderPage(<AdministrationPage />, { get: { clubs: PENDING } });
    expect(loaderShown()).toBe(true);
  });

  it("explains an empty list", async () => {
    renderPage(<AdministrationPage />, { get: { clubs: page([]) } });
    expect(await screen.findByText("No clubs yet")).toBeInTheDocument();
  });

  it("shows the server's message when loading fails", async () => {
    renderPage(<AdministrationPage />, { get: { clubs: FAIL } });
    expect(await screen.findByText("The server is unavailable.")).toBeInTheDocument();
  });

  it("hides Create and Confirm from a role without them", async () => {
    auth.useAuth.mockReturnValue(grant("gymkhana.club.view"));
    renderPage(<AdministrationPage />, { get: { clubs: page([OPEN]) } });
    expect(await screen.findByText("Chess")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /create club/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /confirm/i })).not.toBeInTheDocument();
  });

  it("shows people by name, and says when the directory does not know one", async () => {
    renderPage(<AdministrationPage />, { get: { clubs: page([CLUB]) } });
    expect(await screen.findByText("Student One (stu1001)")).toBeInTheDocument();
    expect(screen.getByText("Faculty One (fac2001)")).toBeInTheDocument();
    expect(screen.getByText("User 1002 (not in the directory)")).toBeInTheDocument();
  });

  it("confirms an open club (UC-GYM-011) and only an open one", async () => {
    const { postSpy } = renderPage(<AdministrationPage />, {
      get: { clubs: page([OPEN, CLUB]) }, post: { "clubs/8/approve": { ...OPEN,
        status: "confirmed" } } });
    await userEvent.click(await screen.findByRole("button", { name: "Confirm Chess" }));
    expect(screen.queryByRole("button", { name: "Confirm Robotics" })).not.toBeInTheDocument();
    await waitFor(() => expect(postSpy).toHaveBeenCalledWith("/gymkhana/clubs/8/approve", {}));
    expect(await screen.findByText("Club confirmed")).toBeInTheDocument();
  });

  it("shows a refusal as sent", async () => {
    renderPage(<AdministrationPage />, { get: { clubs: page([OPEN]) },
      post: { "clubs/8/approve": refusal(409, "This club is already confirmed.") } });
    await userEvent.click(await screen.findByRole("button", { name: "Confirm Chess" }));
    expect(await screen.findByText("This club is already confirmed.")).toBeInTheDocument();
  });

  it("opens the create form with every field labelled (UC-GYM-001)", async () => {
    renderPage(<AdministrationPage />, { get: { clubs: page([]) } });
    await userEvent.click(await screen.findByRole("button", { name: /create club/i }));
    for (const label of [/^name/i, /^category/i, /^description/i, /^coordinator/i,
      /^co-coordinator/i, /club faculty councillor/i]) {
      expect((await screen.findAllByLabelText(label)).length).toBeGreaterThan(0);
    }
    expect(screen.getByRole("button", { name: "Create club" })).toBeDisabled();
  });
});
