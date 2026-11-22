import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CLUB, FAIL, PENDING, STUDENT_PERMS, grant, loaderShown, page, refusal,
  renderPage } from "../testing";
import SchedulePage from "./SchedulePage";

const auth = vi.hoisted(() => ({ useAuth: vi.fn() }));
vi.mock("../../../auth/AuthProvider", () => auth);

const BOOKING = { id: 9, club: 7, club_name: "Robotics", kind: "session",
  venue_name: "LHTC 101", date: "2026-12-01", start_time: "10:00:00", end_time: "11:00:00",
  description: "Weekly build", poster_link: "", event_name: "", faculty_user_id: null,
  created_at: "2026-11-22" };
const LEADER = { "me/clubs": { leading: [CLUB], member_of: [] },
  venues: { venues: ["LHTC 101"] } };

async function fillSession() {
  await userEvent.click(await screen.findByRole("textbox", { name: "Club" }));
  await userEvent.click(await screen.findByRole("option", { name: "Robotics", hidden: true }));
  await userEvent.click(screen.getByRole("textbox", { name: "Venue" }));
  await userEvent.click(await screen.findByRole("option", { name: "LHTC 101", hidden: true }));
  await userEvent.type(screen.getByLabelText(/^date/i), "2026-12-01");
  await userEvent.type(screen.getByLabelText(/start time/i), "10:00");
  await userEvent.type(screen.getByLabelText(/end time/i), "11:00");
  await userEvent.type(screen.getByLabelText(/description/i), "Weekly build");
}

describe("SchedulePage", () => {
  beforeEach(() => auth.useAuth.mockReturnValue(grant(...STUDENT_PERMS)));

  it("shows a loader while bookings load", () => {
    renderPage(<SchedulePage />, { get: { bookings: PENDING, ...LEADER } });
    expect(loaderShown()).toBe(true);
  });

  it("explains an empty schedule", async () => {
    renderPage(<SchedulePage />, { get: { bookings: page([]), ...LEADER } });
    expect(await screen.findByText("Nothing scheduled")).toBeInTheDocument();
  });

  it("shows the server's message when loading fails", async () => {
    renderPage(<SchedulePage />, { get: { bookings: FAIL, ...LEADER } });
    expect(await screen.findByText("The server is unavailable.")).toBeInTheDocument();
  });

  it("offers no booking to a student who leads no club", async () => {
    renderPage(<SchedulePage />, { get: { bookings: page([BOOKING]),
      "me/clubs": { leading: [], member_of: [CLUB] } } });
    expect(await screen.findByText("LHTC 101")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /book/i })).not.toBeInTheDocument();
  });

  it("books a session (UC-GYM-002)", async () => {
    const { postSpy } = renderPage(<SchedulePage />, {
      get: { bookings: page([]), ...LEADER }, post: { sessions: BOOKING } });
    await userEvent.click(await screen.findByRole("button", { name: "Book session" }));
    await fillSession();
    await userEvent.click(screen.getByRole("button", { name: "Book" }));
    await waitFor(() => expect(postSpy).toHaveBeenCalledWith("/gymkhana/sessions",
      expect.objectContaining({ club_id: 7, venue: "LHTC 101", start_time: "10:00" })));
    expect(await screen.findByText("Booked")).toBeInTheDocument();
  });

  it("shows the overlap refusal as sent (BR-GYM-006)", async () => {
    renderPage(<SchedulePage />, { get: { bookings: page([]), ...LEADER },
      post: { sessions: refusal(409, "LHTC 101 is already booked from 10:00 to 11:00.") } });
    await userEvent.click(await screen.findByRole("button", { name: "Book session" }));
    await fillSession();
    await userEvent.click(screen.getByRole("button", { name: "Book" }));
    expect(await screen.findByText("LHTC 101 is already booked from 10:00 to 11:00."))
      .toBeInTheDocument();
  });
});
