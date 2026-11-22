import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";

import { http } from "../../lib/http";
import AnnouncementsPage from "./AnnouncementsPage";

vi.mock("../../auth/AuthProvider", () => ({
  useAuth: () => ({ session: { user: { id: 10 }, active_role: "student" } }),
}));
vi.mock("../../lib/http", () => ({ http: { get: vi.fn() } }));

function renderAnnouncements() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <MantineProvider>
      <QueryClientProvider client={client}>
        <AnnouncementsPage />
      </QueryClientProvider>
    </MantineProvider>,
  );
}

beforeEach(() => vi.mocked(http.get).mockReset());

it("shows an empty state when no announcement is relevant", async () => {
  vi.mocked(http.get).mockResolvedValueOnce({ data: { next: null, results: [] } });
  renderAnnouncements();

  expect(await screen.findByText("There are no announcements for you right now."))
    .toBeInTheDocument();
});

it("loads the next page through the shared client and retains the earlier announcements", async () => {
  vi.mocked(http.get)
    .mockResolvedValueOnce({ data: {
      results: [{ id: 2, content: "New announcement", published_at: "2026-11-22T10:00:00Z" }],
      next: "/api/v1/department/announcements?cursor=page-two",
    } })
    .mockResolvedValueOnce({ data: {
      results: [{ id: 1, content: "Earlier announcement", published_at: "2026-11-21T10:00:00Z" }],
      next: null,
    } });
  renderAnnouncements();

  await userEvent.click(await screen.findByRole("button", { name: "Load more announcements" }));

  expect(await screen.findByText("Earlier announcement")).toBeInTheDocument();
  expect(screen.getByText("New announcement")).toBeInTheDocument();
  expect(http.get).toHaveBeenLastCalledWith("/department/announcements", expect.objectContaining({
    params: { cursor: "page-two" },
  }));
});
