/** Renders a page against a mocked HTTP boundary: the shared axios instance. */
import { MantineProvider } from "@mantine/core";
import { Notifications, notifications } from "@mantine/notifications";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { vi } from "vitest";

import { http } from "../../../lib/http";

type Reply = unknown | (() => unknown);

export function refusal(status: number, message: string) {
  return Object.assign(new Error(message), {
    response: { status, data: { error: { code: "x", message, details: [], request_id: "r1" } } },
  });
}

export const page = (...results: unknown[]) => ({ next: null, previous: null, results });

export const access = (permissions: string[], clubs_led: unknown[] = []) =>
  ({ permissions, clubs_led });

function answer(replies: Record<string, Reply>, path: string) {
  if (!(path in replies)) return Promise.reject(new Error(`unexpected request: ${path}`));
  const reply = replies[path];
  const value = typeof reply === "function" ? (reply as () => unknown)() : reply;
  if (value instanceof Error) return Promise.reject(value);
  return value instanceof Promise ? value : Promise.resolve({ data: value, headers: {} });
}

export const pending = () => new Promise(() => undefined);

export function mockHttp(gets: Record<string, Reply>, posts: Record<string, Reply> = {}) {
  vi.spyOn(http, "get").mockImplementation((path: string) => answer(gets, path) as never);
  return vi.spyOn(http, "post").mockImplementation(
    (path: string) => answer(posts, path) as never);
}

/** Choose from one field's own list; earlier lists can still be closing in the page. */
export async function choose(label: RegExp | string, option: string, search?: string) {
  const field = screen.getByRole("textbox", { name: label });
  if (search) await userEvent.type(field, search);
  else await userEvent.click(field);
  const list = await waitFor(() => {
    const id = field.getAttribute("aria-controls");
    const found = id ? document.getElementById(id) : null;
    if (!found) throw new Error("the list is not open");
    return found;
  });
  await userEvent.click(await within(list).findByRole("option", { name: option, hidden: true }));
}

export function show(ui: ReactElement) {
  // The notification store outlives a test, and shows five at a time.
  notifications.clean();
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <MantineProvider>
      <Notifications />
      <QueryClientProvider client={client}>{ui}</QueryClientProvider>
    </MantineProvider>,
  );
}

export const led = { id: 1, name: "Robotics Club", status: "confirmed", faculty_councillor_id: 201 };

export const club = {
  id: 1, name: "Robotics Club", category: "technical", description: "Builds robots",
  coordinator_id: 101, coordinator_name: "Asha", co_coordinator_id: 102,
  co_coordinator_name: "Ravi", faculty_councillor_id: 201, faculty_councillor_name: "Dr Rao",
  status: "confirmed", created_at: "2026-11-01T10:00:00Z", updated_at: "2026-11-01T10:00:00Z",
};

export const membership = {
  id: 7, club_id: 1, club_name: "Robotics Club", student_id: 103, student_name: "Meera",
  description: "Won a contest", status: "open", remarks: "", applied_at: "2026-11-02T10:00:00Z",
  approved_at: null, approved_by_id: null,
};

export const poll = {
  id: 5, club_id: 1, club_name: "Robotics Club", created_by_id: 101, title: "Next workshop",
  description: "", expires_at: "2099-01-01T10:00:00Z", status: "active",
  created_at: "2026-11-02T10:00:00Z", has_voted: false,
  choices: [{ id: 51, choice_text: "Arduino", vote_count: 1 },
    { id: 52, choice_text: "ROS", vote_count: 3 }],
  target_groups: [{ batch: "2024", branch: "CSE" }],
};

export const booking = {
  id: 9, club_id: 1, club_name: "Robotics Club", booking_type: "event", venue: "Hall 1",
  booking_date: "2026-12-10", start_time: "10:00:00", end_time: "11:00:00", name: "Expo",
  description: "", poster_file: "/gymkhana/bookings/9/poster/", faculty_councillor_id: 201,
  booked_by_id: 101, created_at: "2026-11-02T10:00:00Z",
};

export const report = {
  id: 3, club_id: 1, club_name: "Robotics Club", submitted_by_id: 101, student_incharge_id: 103,
  student_incharge_name: "Meera", event_name: "Expo", event_date: "2026-11-01T10:00:00Z",
  description: "Went well", report_file: "/gymkhana/reports/3/file/",
  submitted_at: "2026-11-02T10:00:00Z",
};
