// Page-test helpers: the shared axios instance is mocked, never the module's own hooks.
import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";

import { http } from "../../lib/http";

type Reply = unknown | { status: number; message: string } | "pending";

export function serverError(status: number, message: string) {
  return { status, message };
}

function isError(r: Reply): r is { status: number; message: string } {
  return typeof r === "object" && r !== null && "status" in r && "message" in r
    && Object.keys(r).length === 2;
}

function respond(reply: Reply) {
  if (reply === "pending") return new Promise(() => undefined);
  if (isError(reply)) {
    return Promise.reject({ response: { status: reply.status, data: { error: {
      code: "x", message: reply.message, details: [], request_id: "req-1" } } } });
  }
  return Promise.resolve({ data: reply, headers: {} });
}

let acting: string[] = [];

// Route GET/POST/PUT/PATCH by path prefix; anything unlisted answers an empty list.
export function mockHttp(given: Record<string, Reply>, writes: Record<string, Reply> = {}) {
  const gets: Record<string, Reply> = { acting: { role: "test", permissions: acting }, ...given };
  const pick = (table: Record<string, Reply>, url: string, fallback: Reply) => {
    const path = url.replace(/^\/pms\//, "");
    const key = Object.keys(table).sort((a, b) => b.length - a.length)
      .find((k) => path === k || path.startsWith(`${k}?`) || path.startsWith(`${k}/`)
        && !Object.keys(table).includes(path));
    return key === undefined ? fallback : table[key];
  };
  const get = vi.spyOn(http, "get").mockImplementation((url: string) =>
    respond(pick(gets, url, [])) as never);
  const write = (url: string) => respond(pick(writes, url, {})) as never;
  const post = vi.spyOn(http, "post").mockImplementation(write);
  const put = vi.spyOn(http, "put").mockImplementation(write);
  const patch = vi.spyOn(http, "patch").mockImplementation(write);
  return { get, post, put, patch };
}

export function authAs(useAuth: ReturnType<typeof vi.fn>, permissions: string[], userId = 1001) {
  acting = permissions;
  useAuth.mockReturnValue({
    can: (p: string) => permissions.includes(p),
    session: { user: { id: userId, username: "u", display_name: "U", kind: "student", email: "" },
      permissions, modules: ["pms"], roles: [], active_role: "student", navigation: [],
      csrf_token: "t" },
    status: "authenticated", switchRole: vi.fn(), hasModule: () => true, logout: vi.fn(),
  });
}

export function renderPage(ui: ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false },
    mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MantineProvider><MemoryRouter>{ui}</MemoryRouter></MantineProvider>
    </QueryClientProvider>,
  );
}

export function hasLoader(container: HTMLElement) {
  return container.querySelector(".mantine-Loader-root") !== null;
}
