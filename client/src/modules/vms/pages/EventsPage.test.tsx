import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { renderPage, routeGet } from "../test-utils";
import EventsPage from "./EventsPage";

vi.mock("../../../auth/AuthProvider", () => ({ useAuth: () => ({ can: () => true }) }));

const event = (id: number, over: Record<string, unknown> = {}) => ({
  id, name: `Event ${id}`, organizer: "CSE Dept", valid_from: "2026-02-01T09:00:00",
  valid_until: "2026-02-01T17:00:00", status: "draft", fast_lane: false, zone_ids: [], ...over });

describe("EventsPage", () => {
  it("lists events with their window and status", async () => {
    routeGet({ "/vms/events": [event(1), event(2, { fast_lane: true, organizer: "" })] });
    renderPage(<EventsPage />);
    expect(await screen.findByText("Event 1")).toBeInTheDocument();
    expect(screen.getAllByText("Draft")).toHaveLength(2);
    expect(screen.getByText("fast lane")).toBeInTheDocument();
    expect(screen.getByText("No organiser listed")).toBeInTheDocument();
  });

  it("explains when there are no events", async () => {
    routeGet({ "/vms/events": [] });
    renderPage(<EventsPage />);
    expect(await screen.findByText("No events yet")).toBeInTheDocument();
  });

  it("approves the attendees of an event", async () => {
    routeGet({ "/vms/events": [event(3)] });
    const post = vi.spyOn(http, "post").mockResolvedValue({ data: {} });
    renderPage(<EventsPage />);
    await userEvent.click(await screen.findByRole("button", { name: /approve attendees/i }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/vms/events/3/approve", {}));
  });

  it("cancels only with a reason", async () => {
    routeGet({ "/vms/events": [event(3)] });
    const post = vi.spyOn(http, "post").mockResolvedValue({ data: {} });
    renderPage(<EventsPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Cancel" }));
    const dialog = await screen.findByRole("dialog");
    const go = within(dialog).getByRole("button", { name: "Cancel event" });
    expect(go).toBeDisabled();
    await userEvent.type(within(dialog).getByLabelText(/reason/i), "Venue unavailable");
    await userEvent.click(go);
    await waitFor(() => expect(post).toHaveBeenCalledWith(
      "/vms/events/3/cancel", { reason: "Venue unavailable" }));
  });

  it("offers no actions on a cancelled event", async () => {
    routeGet({ "/vms/events": [event(5, { status: "cancelled" })] });
    renderPage(<EventsPage />);
    await screen.findByText("Event 5");
    expect(screen.queryByRole("button", { name: /approve attendees/i })).not.toBeInTheDocument();
  });
});
