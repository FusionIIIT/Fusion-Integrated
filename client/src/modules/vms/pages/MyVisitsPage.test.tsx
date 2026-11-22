import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { apiError, renderPage, routeGet } from "../test-utils";
import MyVisitsPage from "./MyVisitsPage";

const auth = vi.hoisted(() => ({ perms: new Set<string>() }));
vi.mock("../../../auth/AuthProvider", () => ({
  useAuth: () => ({ can: (p: string) => auth.perms.has(p) }),
}));

const note = (id: number, read: string | null) => ({
  id, topic: "request.submitted", subject: `Update ${id}`, body: `Body ${id}`,
  created_at: "2026-01-05T09:30:00", read_at: read });

beforeEach(() => { auth.perms = new Set(["vms.notification.view_self"]); });

describe("MyVisitsPage", () => {
  it("shows notifications with unread ones marked, and does not ask for arrivals without host rights", async () => {
    const get = routeGet({ "/vms/notify/inbox": { results: [note(1, null), note(2, "2026-01-05T10:00:00")] } });
    renderPage(<MyVisitsPage />);
    expect(await screen.findByText("Update 1")).toBeInTheDocument();
    expect(screen.getByText("new")).toBeInTheDocument();
    expect(get).not.toHaveBeenCalledWith("/vms/notify/arrivals", expect.anything());
  });

  it("shows arrivals to a host", async () => {
    auth.perms = new Set(["vms.notification.view_self", "vms.request.view_assigned"]);
    routeGet({
      "/vms/notify/inbox": { results: [] },
      "/vms/notify/arrivals": { results: [{ notification: note(9, null), checked_in_at: "2026-01-05T09:45:00", request: null }] },
    });
    renderPage(<MyVisitsPage />);
    expect(await screen.findByText("Visitors who have arrived")).toBeInTheDocument();
    expect(screen.getByText("Update 9")).toBeInTheDocument();
  });

  it("marks one notification read", async () => {
    routeGet({ "/vms/notify/inbox": { results: [note(1, null)] } });
    const post = vi.spyOn(http, "post").mockResolvedValue({ data: {} });
    renderPage(<MyVisitsPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Mark read" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/vms/notify/1/read"));
  });

  it("disables Mark all read when everything is read, and marks all when not", async () => {
    routeGet({ "/vms/notify/inbox": { results: [note(1, "2026-01-05T10:00:00")] } });
    renderPage(<MyVisitsPage />);
    expect(await screen.findByRole("button", { name: /mark all read/i })).toBeDisabled();
  });

  it("marks all read in one call", async () => {
    routeGet({ "/vms/notify/inbox": { results: [note(1, null), note(2, null)] } });
    const post = vi.spyOn(http, "post").mockResolvedValue({ data: { marked: 2 } });
    renderPage(<MyVisitsPage />);
    await userEvent.click(await screen.findByRole("button", { name: /mark all read/i }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/vms/notify/read-all"));
  });

  it("explains an empty inbox", async () => {
    routeGet({ "/vms/notify/inbox": { results: [] } });
    renderPage(<MyVisitsPage />);
    expect(await screen.findByText("No notifications yet")).toBeInTheDocument();
  });

  it("shows the server's message when the inbox fails", async () => {
    vi.spyOn(http, "get").mockRejectedValue(apiError(403, "You cannot view this."));
    renderPage(<MyVisitsPage />);
    expect(await screen.findByText("You cannot view this.")).toBeInTheDocument();
  });
});
