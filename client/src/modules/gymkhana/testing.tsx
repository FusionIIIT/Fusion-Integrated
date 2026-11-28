/** Test harness for gymkhana pages: real hooks, the shared axios instance stubbed per URL. */
import { MantineProvider } from "@mantine/core";
import { Notifications } from "@mantine/notifications";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { vi } from "vitest";

import { http } from "../../lib/http";

type Reply = unknown | ((body: unknown) => unknown);
export type Routes = Record<string, Reply>;

export const PENDING = Symbol("pending");
export const FAIL = Symbol("fail");

function failure(message = "The server is unavailable.") {
  return Object.assign(new Error(message), {
    response: { status: 500, data: { error: { code: "server_error", message, details: [],
      request_id: "req-1" } } },
  });
}

export function refusal(status: number, message: string) {
  return Object.assign(new Error(message), {
    response: { status, data: { error: { code: "refused", message, details: [],
      request_id: "req-2" } } },
  });
}

function answer(routes: Routes, url: string, body?: unknown) {
  const path = url.replace(/^\/gymkhana\//, "");
  if (!(path in routes)) return Promise.reject(failure(`No stub for ${path}`));
  const reply = routes[path];
  if (reply === PENDING) return new Promise(() => undefined);
  if (reply === FAIL) return Promise.reject(failure());
  if (reply instanceof Error) return Promise.reject(reply);
  const data = typeof reply === "function" ? (reply as (b: unknown) => unknown)(body) : reply;
  return Promise.resolve({ data });
}

export function renderPage(ui: ReactElement, { get = {}, post = {} }: {
  get?: Routes; post?: Routes;
} = {}) {
  vi.spyOn(http, "get").mockImplementation((url: string) => answer(get, url));
  const postSpy = vi.spyOn(http, "post").mockImplementation(
    (url: string, body?: unknown) => answer(post, url, body));
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(
    <MantineProvider>
      <Notifications />
      <QueryClientProvider client={qc}>{ui}</QueryClientProvider>
    </MantineProvider>,
  );
  return { postSpy };
}

export function page<T>(results: T[]) {
  return { results, next: null, previous: null };
}

export function loaderShown() {
  return document.querySelector(".mantine-Loader-root") !== null;
}

export function grant(...perms: string[]) {
  const set = new Set(perms);
  return { can: (p: string) => set.has(p), session: null, status: "authenticated",
    hasModule: () => true, switchRole: vi.fn(), logout: vi.fn() };
}

export const CLUB = {
  id: 7, name: "Robotics", category: "technical", description: "Builds robots.",
  status: "confirmed", faculty_councillor_user_id: 2001,
  councillor_name: "Faculty One (fac2001)", approved_at: "2026-11-01",
  created_at: "2026-11-01", leaders: { coordinator: 1001, co_coordinator: 1002 },
  leader_names: { coordinator: "Student One (stu1001)", co_coordinator: "" },
  my_membership: null,
} as const;

export const STUDENT_PERMS = [
  "gymkhana.club.view", "gymkhana.membership.view", "gymkhana.membership.create",
  "gymkhana.poll.view", "gymkhana.vote.create", "gymkhana.booking.view",
  "gymkhana.leadership.assign", "gymkhana.membership.approve", "gymkhana.booking.create",
  "gymkhana.poll.create", "gymkhana.budget_request.view", "gymkhana.budget_request.create",
  "gymkhana.event_report.view", "gymkhana.event_report.create",
];
