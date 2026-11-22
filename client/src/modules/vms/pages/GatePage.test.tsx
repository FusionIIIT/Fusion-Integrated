import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import { apiError, renderPage, routeGet } from "../test-utils";
import GatePage from "./GatePage";

const auth = vi.hoisted(() => ({ perms: new Set<string>() }));
vi.mock("../../../auth/AuthProvider", () => ({
  useAuth: () => ({ can: (p: string) => auth.perms.has(p) }),
}));

const denial = {
  id: 5, visit_pass_id: 2, visitor_name: "Wanda", gate_id: 1, failures: ["outside_validity"],
  overridden: false, escalated: false, created_at: "2026-01-05T09:30:00" };

beforeEach(() => {
  auth.perms = new Set(["vms.gate.operate"]);
  window.localStorage.clear();
  routeGet({ "/vms/gate/denials": { results: [] } });
});

async function enter(credential: string, gate = "3") {
  const gateBox = screen.getByLabelText(/gate's number/i);
  await userEvent.clear(gateBox);
  await userEvent.type(gateBox, gate);
  await userEvent.type(screen.getByLabelText(/QR code or 6-digit OTP/i), credential);
}

describe("GatePage", () => {
  it("keeps Check in disabled until there is both a gate and a credential", async () => {
    renderPage(<GatePage />);
    const checkIn = screen.getByRole("button", { name: /check in/i });
    expect(checkIn).toBeDisabled();
    await enter("123456");
    expect(checkIn).toBeEnabled();
  });

  it("checks a visitor in and shows who was let through, clearing the box for the next scan", async () => {
    const post = vi.spyOn(http, "post").mockResolvedValue({
      data: { detail: "Checked in.", visitor_name: "Ravi Kumar", visit_log_id: 8 } });
    renderPage(<GatePage />);
    await enter("123456");
    await userEvent.click(screen.getByRole("button", { name: /check in/i }));
    await waitFor(() => expect(post).toHaveBeenCalledWith(
      "/vms/gate/validate", { otp: "123456", gate_id: 3 }));
    expect(await screen.findByText("Ravi Kumar")).toBeInTheDocument();
    expect(screen.getByLabelText(/QR code or 6-digit OTP/i)).toHaveValue("");
  });

  it("submits on Enter, the way a scanner does", async () => {
    const post = vi.spyOn(http, "post").mockResolvedValue({ data: { detail: "Checked in.", visitor_name: "Q" } });
    renderPage(<GatePage />);
    await enter("tokenvalue{Enter}");
    await waitFor(() => expect(post).toHaveBeenCalled());
  });

  it("shows a refusal with its reason, and says an Admin can override when eligible", async () => {
    vi.spyOn(http, "post").mockRejectedValue(Object.assign(new Error("denied"), {
      response: { status: 403, data: {
        detail: "The pass has expired.", code: "outside_validity",
        override_eligible: true, failures: [] } } }));
    renderPage(<GatePage />);
    await enter("123456");
    await userEvent.click(screen.getByRole("button", { name: /check in/i }));
    expect(await screen.findByText("Entry refused")).toBeInTheDocument();
    expect(screen.getByText("The pass has expired.")).toBeInTheDocument();
    expect(screen.getByText(/Admin can override/)).toBeInTheDocument();
  });

  it("shows a server fault as a refusal message and does not pretend the visitor got in", async () => {
    vi.spyOn(http, "post").mockRejectedValue(apiError(500, "Gate service unavailable."));
    renderPage(<GatePage />);
    await enter("123456");
    await userEvent.click(screen.getByRole("button", { name: /check in/i }));
    expect(await screen.findByText("Gate service unavailable.")).toBeInTheDocument();
    expect(screen.getByText("Entry refused")).toBeInTheDocument();
  });

  it("checks a visitor out", async () => {
    const post = vi.spyOn(http, "post").mockResolvedValue({ data: { detail: "Checked out." } });
    renderPage(<GatePage />);
    await enter("abc");
    await userEvent.click(screen.getByRole("button", { name: /check out/i }));
    await waitFor(() => expect(post).toHaveBeenCalledWith(
      "/vms/visit/check-out", { credential: "abc", gate_id: 3 }));
    expect(await screen.findByText("Checked out.")).toBeInTheDocument();
  });

  it("remembers the gate number on this device", async () => {
    const { unmount } = renderPage(<GatePage />);
    await enter("x", "7");
    expect(window.localStorage.getItem("vms.gate_id")).toBe("7");
    unmount();
    renderPage(<GatePage />);
    expect(screen.getByLabelText(/gate's number/i)).toHaveValue("7");
  });

  it("lists denials, and only an Admin sees the Override button", async () => {
    routeGet({ "/vms/gate/denials": { results: [denial] } });
    renderPage(<GatePage />);
    await userEvent.click(await screen.findByRole("tab", { name: /denied entries/i }));
    expect(await screen.findByText("Wanda")).toBeInTheDocument();
    expect(screen.getByText("Outside validity")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Override" })).not.toBeInTheDocument();
  });

  it("overrides a denial only with a justification", async () => {
    auth.perms = new Set(["vms.gate.operate", "vms.gate.override"]);
    routeGet({ "/vms/gate/denials": { results: [denial] } });
    const post = vi.spyOn(http, "post").mockResolvedValue({ data: {} });
    renderPage(<GatePage />);
    await userEvent.click(await screen.findByRole("tab", { name: /denied entries/i }));
    await userEvent.click(await screen.findByRole("button", { name: "Override" }));
    const dialog = await screen.findByRole("dialog");
    const allow = within(dialog).getByRole("button", { name: "Allow entry" });
    expect(allow).toBeDisabled();
    await userEvent.type(within(dialog).getByLabelText(/justification/i), "Escorted by host");
    await userEvent.click(allow);
    await waitFor(() => expect(post).toHaveBeenCalledWith("/vms/gate/override", {
      denial_log_id: 5, justification: "Escorted by host" }));
  });
});
