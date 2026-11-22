import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, it, vi } from "vitest";

import { http } from "../../lib/http";
import AnnouncementsPage from "./AnnouncementsPage";

const access = vi.hoisted(() => ({ publish: false }));
vi.mock("../../auth/AuthProvider", () => ({
  useAuth: () => ({ session: { user: { id: 10 }, active_role: "student" }, can: () => false }),
}));
vi.mock("./DepartmentLayout", () => ({
  useDepartmentCan: () => (code: string) => access.publish && code === "department.announcement.publish",
}));
vi.mock("../../lib/http", async (original) => ({
  ...await original<typeof import("../../lib/http")>(), http: { get: vi.fn(), post: vi.fn() },
}));

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

beforeEach(() => {
  access.publish = false;
  vi.mocked(http.get).mockReset().mockResolvedValue({ data: { next: null, results: [] } });
  vi.mocked(http.post).mockReset().mockResolvedValue({ data: {} });
});

it("shows an empty state when no announcement is relevant", async () => {
  vi.mocked(http.get).mockResolvedValueOnce({ data: { next: null, results: [] } });
  renderAnnouncements();

  expect(await screen.findByText("There are no announcements for you right now."))
    .toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "New announcement" })).not.toBeInTheDocument();
});

it("shows loading while announcements are being fetched", () => {
  vi.mocked(http.get).mockImplementation(() => new Promise(() => {}));
  renderAnnouncements();
  expect(screen.getByLabelText("Loading announcements")).toBeInTheDocument();
});

it("shows an error when announcements cannot be fetched", async () => {
  vi.mocked(http.get).mockRejectedValue(new Error("Request failed"));
  renderAnnouncements();
  expect(await screen.findByText("Could not load this")).toBeInTheDocument();
});

it("publishes an announcement through the authorized control", async () => {
  access.publish = true;
  renderAnnouncements();
  await userEvent.click(screen.getByRole("button", { name: "New announcement" }));
  await userEvent.type(screen.getByLabelText("Announcement", { exact: false }), "Department seminar");
  await userEvent.click(screen.getByRole("button", { name: "Publish" }));
  expect(await screen.findByRole("button", { name: "New announcement" })).toBeInTheDocument();
  expect(http.post).toHaveBeenCalledWith("/department/announcements", {
    content: "Department seminar", target_roles: [], target_programmes: [], target_batch_years: [],
  });
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
