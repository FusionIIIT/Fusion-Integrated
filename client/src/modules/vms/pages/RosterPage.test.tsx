import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { renderPage, routeGet } from "../test-utils";
import RosterPage from "./RosterPage";

const auth = vi.hoisted(() => ({ perms: new Set<string>() }));
vi.mock("../../../auth/AuthProvider", () => ({
  useAuth: () => ({ can: (p: string) => auth.perms.has(p) }),
}));

const visitor = (id: number, over: Record<string, unknown> = {}) => ({
  pass_id: id, visitor_name: `Guest ${id}`, visitor_phone: "9876543210", visitor_email: "",
  zone_id: 1, zone_name: "Lobby", last_seen_at: "2026-01-05T09:30:00",
  valid_until: "2026-01-05T17:00:00", terminated: false, overstay: false,
  host_user_id: 2, host_name: "Prof. Rao", host_department: "CSE", ...over });

const dashboard = { on_site: 2, by_zone: [{ zone_id: 1, zone_name: "Lobby", count: 2 }],
  by_department: [], open_alerts: { total: 3, by_kind: {} }, overstays: { count: 1 },
  as_of: "2026-01-05T10:00:00" };

beforeEach(() => { auth.perms = new Set(["vms.monitor.view"]); });

describe("RosterPage", () => {
  it("shows who is on site with their host and last zone, and the headline counts", async () => {
    routeGet({
      "/vms/monitor/on-site": { count: 2, results: [visitor(1), visitor(2, { overstay: true })] },
      "/vms/monitor/dashboard": dashboard });
    renderPage(<RosterPage />);
    expect(await screen.findByText("Guest 1")).toBeInTheDocument();
    expect(screen.getAllByText("Prof. Rao")).toHaveLength(2);
    expect(screen.getByText("overstay")).toBeInTheDocument();
    expect(await screen.findByText("Open alerts")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("says nobody is on site rather than showing an empty table", async () => {
    routeGet({ "/vms/monitor/on-site": { count: 0, results: [] }, "/vms/monitor/dashboard": dashboard });
    renderPage(<RosterPage />);
    expect(await screen.findByText("Nobody is on site")).toBeInTheDocument();
  });

  it("offers no Terminate button without the permission", async () => {
    routeGet({ "/vms/monitor/on-site": { count: 1, results: [visitor(1)] },
      "/vms/monitor/dashboard": dashboard });
    renderPage(<RosterPage />);
    await screen.findByText("Guest 1");
    expect(screen.queryByRole("button", { name: "Terminate" })).not.toBeInTheDocument();
  });

  it("terminates a visit only with a reason, and not for a pass already pending exit", async () => {
    auth.perms = new Set(["vms.monitor.view", "vms.pass.terminate"]);
    routeGet({
      "/vms/monitor/on-site": { count: 2, results: [visitor(1), visitor(2, { terminated: true })] },
      "/vms/monitor/dashboard": dashboard });
    const post = vi.spyOn(http, "post").mockResolvedValue({ data: {} });
    renderPage(<RosterPage />);
    await screen.findByText("Guest 1");
    expect(screen.getAllByRole("button", { name: "Terminate" })).toHaveLength(1);
    expect(screen.getByText("pending exit")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Terminate" }));
    const dialog = await screen.findByRole("dialog");
    const go = within(dialog).getByRole("button", { name: "Terminate" });
    expect(go).toBeDisabled();
    await userEvent.type(within(dialog).getByLabelText(/reason/i), "Policy breach");
    await userEvent.click(go);
    await waitFor(() => expect(post).toHaveBeenCalledWith(
      "/vms/visit/passes/1/terminate", { reason: "Policy breach" }));
  });
});
