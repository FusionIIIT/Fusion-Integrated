import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { renderPage, routeGet } from "../test-utils";
import AdminPage from "./AdminPage";

const auth = vi.hoisted(() => ({ perms: new Set<string>() }));
vi.mock("../../../auth/AuthProvider", () => ({
  useAuth: () => ({ can: (p: string) => auth.perms.has(p) }),
}));

const policy = (id: number, version: number, status: string) => ({
  id, version, status, published_at: status === "published" ? "2026-01-01T09:00:00" : null,
  visiting_hours_start: "08:00:00", visiting_hours_end: "20:00:00", max_visit_hours: 8,
  walk_in_pass_hours: 4, approval_timeout_hours: 24, advance_registration_hours: 2 });

beforeEach(() => { auth.perms = new Set(["vms.policy.manage"]); });

describe("AdminPage", () => {
  it("shows only the tabs the user's permissions allow", async () => {
    routeGet({ "/vms/policies": [] });
    renderPage(<AdminPage />);
    expect(await screen.findByRole("tab", { name: /policies/i })).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: /blacklist/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: /roles/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: /zones/i })).not.toBeInTheDocument();
  });

  it("lists policy versions and lets a publisher publish a draft", async () => {
    auth.perms = new Set(["vms.policy.manage", "vms.policy.publish"]);
    routeGet({ "/vms/policies": [policy(1, 1, "published"), policy(2, 2, "draft")] });
    const post = vi.spyOn(http, "post").mockResolvedValue({ data: {} });
    renderPage(<AdminPage />);
    expect(await screen.findByText("v2")).toBeInTheDocument();
    expect(screen.getAllByText("08:00 – 20:00", { selector: "td" })).toHaveLength(2);
    expect(screen.getAllByRole("button", { name: "Publish" })).toHaveLength(1);
    await userEvent.click(screen.getByRole("button", { name: "Publish" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/vms/policies/2/publish"));
  });

  it("does not let a manager without publish rights publish", async () => {
    routeGet({ "/vms/policies": [policy(2, 2, "draft")] });
    renderPage(<AdminPage />);
    await screen.findByText("v2");
    expect(screen.queryByRole("button", { name: "Publish" })).not.toBeInTheDocument();
  });

  it("lists only live role assignments and revokes one", async () => {
    auth.perms = new Set(["vms.policy.manage", "vms.role.assign"]);
    routeGet({ "/vms/policies": [], "/vms/roles": [
      { id: 1, user_id: 10, role: "security", scope_type: "gate", scope_id: 3,
        starts_at: "2026-01-01T00:00:00", ends_at: "2026-03-01T00:00:00", revoked_at: null },
      { id: 2, user_id: 11, role: "admin", scope_type: "campus", scope_id: null,
        starts_at: "2026-01-01T00:00:00", ends_at: "2026-03-01T00:00:00",
        revoked_at: "2026-01-02T00:00:00" }] });
    const post = vi.spyOn(http, "post").mockResolvedValue({ data: {} });
    renderPage(<AdminPage />);
    await userEvent.click(await screen.findByRole("tab", { name: /roles/i }));
    expect(await screen.findByText("User 10")).toBeInTheDocument();
    expect(screen.queryByText("User 11")).not.toBeInTheDocument();
    expect(screen.getByText("Gate 3")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Revoke" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/vms/roles/1/revoke"));
  });

  it("lists zones and flags restricted ones", async () => {
    auth.perms = new Set(["vms.policy.manage", "vms.zone.manage"]);
    routeGet({ "/vms/policies": [], "/vms/zones": [
      { id: 1, name: "Lobby", is_restricted: false, is_active: true },
      { id: 2, name: "Hostel", is_restricted: true, is_active: true }] });
    renderPage(<AdminPage />);
    await userEvent.click(await screen.findByRole("tab", { name: /zones/i }));
    expect(await screen.findByText("Hostel")).toBeInTheDocument();
    expect(screen.getByText("Restricted")).toBeInTheDocument();
  });

  it("lists blacklist versions and publishes a draft", async () => {
    auth.perms = new Set(["vms.policy.manage", "vms.blacklist.manage", "vms.blacklist.publish"]);
    routeGet({ "/vms/policies": [], "/vms/blacklist/versions": [
      { id: 7, version: 3, status: "draft", published_at: null }] });
    const post = vi.spyOn(http, "post").mockResolvedValue({ data: {} });
    renderPage(<AdminPage />);
    await userEvent.click(await screen.findByRole("tab", { name: /blacklist/i }));
    await userEvent.click(await screen.findByRole("button", { name: "Publish" }));
    await waitFor(() => expect(post).toHaveBeenCalledWith("/vms/blacklist/versions/7/publish"));
  });
});
