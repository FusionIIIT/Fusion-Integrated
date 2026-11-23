import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import {
  access, booking, choose, led, membership, mockHttp, page, pending, poll, refusal, show,
} from "../test/harness";
import ClubManagementPage from "./ClubManagementPage";

const person = { results: [{ user_id: 103, username: "u", display_name: "Person" }] };
const gets = (over = {}) => ({
  "/gymkhana/access/": access(["gymkhana.club.manage"], [led]),
  "/gymkhana/memberships/": page(membership),
  "/gymkhana/bookings/": page(booking),
  "/gymkhana/venues/": { venues: ["Hall 1"] },
  "/gymkhana/polls/": page(poll),
  "/gymkhana/poll-options/": { batches: ["2024"], branches: ["CSE"] },
  "/gymkhana/budgets/": page(),
  "/gymkhana/people/": person,
  ...over,
});

async function openTab(name: string) {
  await userEvent.click(await screen.findByRole("tab", { name }));
}

async function pickPerson(label: RegExp) {
  await choose(label, "Person (u)", "per");
}

const pdf = () => new File(["x"], "paper.pdf", { type: "application/pdf" });

function attach(container: HTMLElement) {
  const input = container.ownerDocument.querySelector<HTMLInputElement>("input[type=file]");
  if (!input) throw new Error("no file input on screen");
  return userEvent.upload(input, pdf());
}

describe("ClubManagementPage", () => {
  it("shows a loading state", () => {
    mockHttp(gets({ "/gymkhana/access/": pending }));
    show(<ClubManagementPage />);
    expect(screen.getByLabelText("Loading your clubs")).toBeInTheDocument();
  });

  it("offers nothing to someone who leads no club", async () => {
    mockHttp(gets({ "/gymkhana/access/": access(["gymkhana.club.manage"]) }));
    show(<ClubManagementPage />);
    expect(await screen.findByText("You do not lead a club.")).toBeInTheDocument();
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
    expect(screen.queryByRole("tab")).not.toBeInTheDocument();
  });

  it("shows the server's error", async () => {
    mockHttp(gets({ "/gymkhana/access/": refusal(500, "Database is down") }));
    show(<ClubManagementPage />);
    expect(await screen.findByText("Database is down")).toBeInTheDocument();
  });

  it("says when the club is not confirmed yet", async () => {
    mockHttp(gets({ "/gymkhana/access/": access([], [{ ...led, status: "open" }]) }));
    show(<ClubManagementPage />);
    expect(await screen.findByText("Awaiting approval")).toBeInTheDocument();
  });

  it("approves several applications, each on its own", async () => {
    const second = { ...membership, id: 8, student_name: "Nikhil" };
    const post = mockHttp(gets({ "/gymkhana/memberships/": page(membership, second) }), {
      "/gymkhana/memberships/7/approve/": membership,
      "/gymkhana/memberships/8/approve/": refusal(409, "No longer open."),
    });
    show(<ClubManagementPage />);
    await userEvent.click(await screen.findByLabelText("Select all on this page"));
    await userEvent.type(screen.getByLabelText("Remarks (optional)"), "Welcome");
    await userEvent.click(screen.getByRole("button", { name: "Approve selected" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith(
      "/gymkhana/memberships/7/approve/", { remarks: "Welcome" }));
    expect(await screen.findByText("1 approved.")).toBeInTheDocument();
    expect(await screen.findByText("No longer open.")).toBeInTheDocument();
  });

  it("books a session, and refuses a backwards time before sending", async () => {
    const post = mockHttp(gets(), { "/gymkhana/bookings/session/": booking });
    show(<ClubManagementPage />);
    await openTab("Bookings");
    await userEvent.click(await screen.findByRole("button", { name: "Book session" }));
    await choose(/venue/i, "Hall 1");
    await userEvent.type(screen.getByLabelText(/^date/i), "2026-12-10");
    await userEvent.type(screen.getByLabelText(/start time/i), "11:00");
    await userEvent.type(screen.getByLabelText(/end time/i), "10:00");
    const book = screen.getByRole("button", { name: "Book" });
    expect(book).toBeDisabled();
    expect(screen.getByText("The start time must be before the end time.")).toBeInTheDocument();
    await userEvent.clear(screen.getByLabelText(/end time/i));
    await userEvent.type(screen.getByLabelText(/end time/i), "12:00");
    await userEvent.click(book);
    await waitFor(() => expect(post).toHaveBeenCalled());
    const body = post.mock.calls[0]?.[1] as FormData;
    expect(body.get("venue")).toBe("Hall 1");
    expect(body.has("faculty_councillor_id")).toBe(false);
  });

  it("shows a refused event booking as the server sent it", async () => {
    mockHttp(gets(), { "/gymkhana/bookings/event/": refusal(409, "Hall 1 is already booked.") });
    show(<ClubManagementPage />);
    await openTab("Bookings");
    await userEvent.click(await screen.findByRole("button", { name: "Book event" }));
    await userEvent.type(screen.getByRole("textbox", { name: /event name/i }), "Expo");
    await pickPerson(/faculty councillor/i);
    await choose(/venue/i, "Hall 1");
    await userEvent.type(screen.getByLabelText(/^date/i), "2026-12-10");
    await userEvent.type(screen.getByLabelText(/start time/i), "10:00");
    await userEvent.type(screen.getByLabelText(/end time/i), "11:00");
    await userEvent.click(screen.getByRole("button", { name: "Book" }));
    expect(await screen.findByText("Hall 1 is already booked.")).toBeInTheDocument();
  });

  it("creates a poll for a chosen group", async () => {
    const post = mockHttp(gets(), { "/gymkhana/polls/": poll });
    show(<ClubManagementPage />);
    await openTab("Polls");
    expect(await screen.findByText("3 of 4")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Create poll" }));
    await userEvent.type(screen.getByRole("textbox", { name: /^title/i }), "Theme");
    await userEvent.type(screen.getByLabelText(/closes at/i), "2099-01-01T10:00");
    await userEvent.type(screen.getByRole("textbox", { name: /choice 1/i }), "Space");
    await userEvent.type(screen.getByRole("textbox", { name: /choice 2/i }), "Ocean");
    const create = screen.getByRole("button", { name: "Create" });
    expect(create).toBeDisabled();
    await choose("Batch", "2024");
    await choose("Branch", "All branches");
    await userEvent.click(screen.getByRole("button", { name: "Add group" }));
    expect(screen.getByRole("button", { name: "Remove group 2024 / all" })).toBeInTheDocument();
    await userEvent.click(create);
    await waitFor(() => expect(post).toHaveBeenCalledWith("/gymkhana/polls/",
      expect.objectContaining({
        title: "Theme", choices: ["Space", "Ocean"],
        target_groups: [{ batch: "2024", branch: "all" }],
      })));
  });

  it("submits a budget request only with its file", async () => {
    const post = mockHttp(gets(), { "/gymkhana/budgets/": {} });
    const { container } = show(<ClubManagementPage />);
    await openTab("Budget requests");
    expect(await screen.findByText("No budget requests yet")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Request budget" }));
    await userEvent.type(screen.getByRole("textbox", { name: /purpose/i }), "Kit");
    await userEvent.type(screen.getByLabelText(/amount/i), "500");
    const submit = screen.getByRole("button", { name: "Submit request" });
    expect(submit).toBeDisabled();
    await attach(container);
    await userEvent.click(submit);
    await waitFor(() => expect(post).toHaveBeenCalled());
    const body = post.mock.calls[0]?.[1] as FormData;
    expect((body.get("supporting_file") as File).name).toBe("paper.pdf");
  });

  it("submits an event report", async () => {
    const post = mockHttp(gets(), { "/gymkhana/reports/": {} });
    const { container } = show(<ClubManagementPage />);
    await openTab("Event report");
    await userEvent.type(await screen.findByRole("textbox", { name: /event name/i }), "Expo");
    await userEvent.type(screen.getByLabelText(/event date and time/i), "2026-11-01T10:00");
    await pickPerson(/student incharge/i);
    await attach(container);
    await userEvent.click(screen.getByRole("button", { name: "Submit report" }));
    await waitFor(() => expect(post).toHaveBeenCalled());
    expect((post.mock.calls[0]?.[1] as FormData).get("student_incharge_id")).toBe("103");
    expect(await screen.findByText("Report submitted")).toBeInTheDocument();
  });

  it("replaces both leaders, and says so even though the club is then no longer theirs", async () => {
    let handedOver = false;
    const post = mockHttp(gets({
      "/gymkhana/access/": () => access([], handedOver ? [] : [led]),
    }), { "/gymkhana/clubs/1/leadership/": () => { handedOver = true; return {}; } });
    show(<ClubManagementPage />);
    await openTab("Leadership");
    await userEvent.click(await screen.findByRole("button", { name: "Change leadership" }));
    await pickPerson(/new coordinator/i);
    await pickPerson(/new co-coordinator/i);
    await userEvent.click(screen.getByRole("button", { name: "Replace leaders" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/gymkhana/clubs/1/leadership/",
      { coordinator_id: 103, co_coordinator_id: 103 }));
    expect(await screen.findByText("Leadership changed")).toBeInTheDocument();
    expect(await screen.findByText("You do not lead a club.")).toBeInTheDocument();
  });
});
