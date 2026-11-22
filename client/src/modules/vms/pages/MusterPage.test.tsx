import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { renderPage, routeGet } from "../test-utils";
import MusterPage from "./MusterPage";

const auth = vi.hoisted(() => ({ perms: new Set<string>() }));
vi.mock("../../../auth/AuthProvider", () => ({
  useAuth: () => ({ can: (p: string) => auth.perms.has(p) }),
}));

const muster = { id: 4, status: "open", trigger_role: "security", triggered_by_user_id: 1,
  triggered_at: "2026-01-05T09:00:00", closed_at: null, reason: "Fire drill", counts: {} };
const entry = (id: number, status: string) => ({
  pass_id: id, visitor_name: `Guest ${id}`, last_zone_name: "Lobby", host_name: "Prof. Rao", status });

beforeEach(() => { auth.perms = new Set(["vms.muster.rollcall", "vms.muster.trigger"]); });

describe("MusterPage", () => {
  it("offers to start a muster only to someone who may, and only when none is open", async () => {
    routeGet({ "/vms/muster/current": { muster: null } });
    renderPage(<MusterPage />);
    expect(await screen.findByText("No muster in progress")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /start emergency muster/i })).toBeInTheDocument();
  });

  it("hides the start button without the trigger permission", async () => {
    auth.perms = new Set(["vms.muster.rollcall"]);
    routeGet({ "/vms/muster/current": { muster: null } });
    renderPage(<MusterPage />);
    await screen.findByText("No muster in progress");
    expect(screen.queryByRole("button", { name: /start emergency muster/i })).not.toBeInTheDocument();
  });

  it("starts a muster with the reason given", async () => {
    routeGet({ "/vms/muster/current": { muster: null } });
    const post = vi.spyOn(http, "post").mockResolvedValue({ data: muster });
    renderPage(<MusterPage />);
    await userEvent.click(await screen.findByRole("button", { name: /start emergency muster/i }));
    const dialog = await screen.findByRole("dialog");
    await userEvent.type(within(dialog).getByLabelText(/reason/i), "Fire drill");
    await userEvent.click(within(dialog).getByRole("button", { name: "Start muster" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/vms/muster", { reason: "Fire drill" }));
  });

  it("shows the open muster, the roll call and how many are accounted for", async () => {
    routeGet({
      "/vms/muster/current": { muster },
      "/vms/muster/4/roster": { count: 2, results: [entry(1, "accounted"), entry(2, "pending")] } });
    renderPage(<MusterPage />);
    expect(await screen.findByText(/Emergency muster open since/)).toBeInTheDocument();
    expect(await screen.findByText(/1 of 2 visitors accounted for/)).toBeInTheDocument();
    expect(screen.getByText("Guest 2")).toBeInTheDocument();
  });

  it("marks a visitor accounted for", async () => {
    routeGet({ "/vms/muster/current": { muster },
      "/vms/muster/4/roster": { count: 1, results: [entry(2, "pending")] } });
    const post = vi.spyOn(http, "post").mockResolvedValue({ data: {} });
    renderPage(<MusterPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Accounted" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith(
      "/vms/muster/4/roll-call", { pass_id: 2, status: "accounted" }));
  });

  it("forces the close and says so when visitors are still unaccounted for", async () => {
    routeGet({ "/vms/muster/current": { muster },
      "/vms/muster/4/roster": { count: 1, results: [entry(2, "pending")] } });
    const post = vi.spyOn(http, "post").mockResolvedValue({ data: {} });
    renderPage(<MusterPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Close muster" }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText(/1 visitors are not yet accounted for/)).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole("button", { name: "Close muster" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith(
      "/vms/muster/4/close", { note: "", force: true }));
  });
});
