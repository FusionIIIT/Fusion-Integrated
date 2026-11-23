// Shared harness for PHC page tests: real hooks, HTTP mocked at the shared axios instance.
import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactElement } from "react";
import { expect, it, vi } from "vitest";

export const state = {
  permissions: new Set<string>(),
};

export function serverError(message = "The server could not answer.") {
  return Object.assign(new Error("500"), {
    response: { status: 500, data: { error: { code: "error", message, details: [],
      request_id: "req-1" } } },
  });
}

export function refusal(message: string, status = 422) {
  return Object.assign(new Error(String(status)), {
    response: { status, data: { error: { code: "refused", message, details: [],
      request_id: "req-2" } } },
  });
}

export function renderPage(ui: ReactElement) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}><MantineProvider>{ui}</MantineProvider></QueryClientProvider>,
  );
}

type Getter = ReturnType<typeof vi.fn>;

// The loading, empty and error cases every list page must render honestly.
export function listStateTests(opts: {
  get: Getter;
  page: () => ReactElement;
  empty: unknown;
  emptyText: RegExp;
}) {
  it("shows a loading state", () => {
    opts.get.mockReturnValue(new Promise(() => undefined));
    renderPage(opts.page());
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("shows an empty state", async () => {
    opts.get.mockResolvedValue({ data: opts.empty });
    renderPage(opts.page());
    expect(await screen.findByText(opts.emptyText)).toBeInTheDocument();
  });

  it("shows the server's message when the API fails", async () => {
    opts.get.mockRejectedValue(serverError());
    renderPage(opts.page());
    expect(await screen.findByText("The server could not answer.")).toBeInTheDocument();
    expect(screen.queryByText("Loading…")).not.toBeInTheDocument();
  });
}
