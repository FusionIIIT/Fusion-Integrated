import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { authAs, mockHttp, renderPage, serverError } from "../test-utils";
import SettingsPage from "./SettingsPage";

const auth = vi.hoisted(() => ({ useAuth: vi.fn() }));
vi.mock("../../../auth/AuthProvider", () => auth);

const PERMS = ["pms.policy.publish"];
const POLICY = { version: 1, history: [], payload: { cost_threshold: "100000.00",
  appeal_period_days: 30, alert_offsets_days: [30, 15, 5], withdrawal_statuses: [],
  withdrawal_consent_required: false, holidays: [], domains: [{ code: "materials",
    label: "Materials", ipc_classes: ["H01M"] }], maintenance_rules: { IN: [12, 24] },
  escalation_chain: [], pcc_contact_user_id: null, auto_routing_enabled: false,
  licensing_route: null } };

describe("SettingsPage", () => {
  afterEach(() => vi.restoreAllMocks());

  it("shows nothing editable while loading", () => {
    authAs(auth.useAuth, PERMS);
    mockHttp({ policy: "pending", setup: "pending" });
    renderPage(<SettingsPage />);
    expect(screen.queryByRole("button", { name: /Publish/ })).toBeNull();
  });

  it("lists what is still to configure", async () => {
    authAs(auth.useAuth, PERMS);
    mockHttp({ policy: POLICY, setup: { gaps: ["No Directors are on the roster."] } });
    renderPage(<SettingsPage />);
    expect(await screen.findByText("No Directors are on the roster.")).toBeInTheDocument();
  });

  it("shows the server's message when loading fails", async () => {
    authAs(auth.useAuth, PERMS);
    mockHttp({ policy: serverError(500, "Settings unavailable."), setup: { gaps: [] } });
    renderPage(<SettingsPage />);
    expect(await screen.findByText("Settings unavailable.")).toBeInTheDocument();
  });

  it("shows the current values", async () => {
    authAs(auth.useAuth, PERMS);
    mockHttp({ policy: POLICY, setup: { gaps: [] } });
    renderPage(<SettingsPage />);
    expect(await screen.findByDisplayValue("100000.00")).toBeInTheDocument();
    expect(screen.queryByText("Still to configure")).toBeNull();
  });

  it("publishes a new version and shows a stale-version refusal", async () => {
    authAs(auth.useAuth, PERMS);
    const calls = mockHttp({ policy: POLICY, setup: { gaps: [] } },
      { policy: serverError(409, "The settings changed (now version 2).") });
    renderPage(<SettingsPage />);
    const threshold = await screen.findByRole("textbox", { name: "Budget threshold (Rs)" });
    await userEvent.clear(threshold);
    await userEvent.type(threshold, "5000");
    await userEvent.click(screen.getByRole("button", { name: "Publish version 2" }));
    await waitFor(() => expect(calls.post).toHaveBeenCalledWith("/pms/policy",
      expect.objectContaining({ based_on_version: 1,
        payload: expect.objectContaining({ cost_threshold: "5000" }) })));
    expect(await screen.findByText("The settings changed (now version 2).")).toBeInTheDocument();
  });

  it("still confirms the publish after the new version reloads the form", async () => {
    authAs(auth.useAuth, PERMS);
    mockHttp({ policy: POLICY, setup: { gaps: [] } });
    renderPage(<SettingsPage />);
    const publish = await screen.findByRole("button", { name: "Publish version 2" });
    mockHttp({ policy: { ...POLICY, version: 2 }, setup: { gaps: [] } }, { policy: { version: 2 } });
    await userEvent.click(publish);
    expect(await screen.findByText("Version 2 is in effect.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Publish version 3" })).toBeInTheDocument();
  });
});
