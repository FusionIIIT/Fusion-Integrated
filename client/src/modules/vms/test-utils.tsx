import { MantineProvider } from "@mantine/core";
import { Notifications } from "@mantine/notifications";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { vi } from "vitest";

import { http } from "../../lib/http";

/** A page inside the providers the app gives it, with retries off so a failed request
 *  shows its error at once instead of after a backoff. */
export function renderPage(ui: ReactElement) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <MantineProvider>
      <Notifications />
      <QueryClientProvider client={qc}>{ui}</QueryClientProvider>
    </MantineProvider>,
  );
}

type Routes = Record<string, unknown | ((config?: unknown) => unknown)>;

/** Answer GETs by exact path. An unlisted path fails the test loudly, so a page cannot
 *  quietly start calling an endpoint nobody planned for. */
export function routeGet(routes: Routes) {
  return vi.spyOn(http, "get").mockImplementation(async (url: string, config?: unknown) => {
    if (!(url in routes)) throw new Error(`unexpected GET ${url}`);
    const value = routes[url];
    const data = typeof value === "function" ? (value as (c?: unknown) => unknown)(config) : value;
    return { data, headers: {}, status: 200 };
  });
}

export function respondPost(data: unknown = {}) {
  return vi.spyOn(http, "post").mockResolvedValue({ data, headers: {}, status: 200 });
}

/** The envelope the server sends for a refusal. */
export function apiError(status: number, message: string, extra: Record<string, unknown> = {}) {
  return Object.assign(new Error(message), {
    response: { status, data: { error: { message }, ...extra } },
  });
}
