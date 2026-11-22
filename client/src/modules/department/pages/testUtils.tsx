import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { vi } from "vitest";

// Tests mock the shared axios instance (Step 6.7), never the module's own hooks.
export const granted = new Set<string>();

export const authMock = () => ({
  useAuth: () => ({ can: (p: string) => granted.has(p), session: null, status: "authenticated" }),
});

export const api = { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() };

export const httpMock = async (importOriginal: () => Promise<Record<string, unknown>>) => ({
  ...(await importOriginal()),
  http: api,
});

export function setup(perms: string[], routes: Record<string, unknown>) {
  granted.clear();
  perms.forEach((p) => granted.add(p));
  api.get.mockImplementation((url: string) => {
    const key = Object.keys(routes).find((k) => url.endsWith(k));
    const value = key ? routes[key] : { results: [] };
    if (value === "pending") return new Promise(() => undefined);
    if (value instanceof Error) return Promise.reject(value);
    return Promise.resolve({ data: value });
  });
}

export function serverError(message = "Server exploded.", status = 500) {
  return Object.assign(new Error(message), {
    response: { status, data: { error: { code: "x", message, details: [], request_id: "rid-1" } } },
  });
}

export const page = <T,>(results: T[]) => ({ results, next: null, previous: null });

export function renderPage(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}><MantineProvider>{ui}</MantineProvider></QueryClientProvider>,
  );
}
