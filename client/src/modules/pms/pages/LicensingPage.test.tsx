import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { authAs, hasLoader, mockHttp, renderPage, serverError } from "../test-utils";
import LicensingPage from "./LicensingPage";

const auth = vi.hoisted(() => ({ useAuth: vi.fn() }));
vi.mock("../../../auth/AuthProvider", () => auth);

const APPLICANT = ["pms.licensing_request.view", "pms.licensing_request.create"];
const REQ = { id: 3, application_id: 7, application_reference: "PMS-2026-00007",
  kind: "licensing", summary: "Licence it.", status: "routed", route_kind: "committee",
  routed_director_user_id: null, committee_name: "TTC", routed_at: null, notes: [],
  agreement: null, created_at: "2026-12-01" };

describe("LicensingPage", () => {
  afterEach(() => vi.restoreAllMocks());

  it("shows a spinner while loading", () => {
    authAs(auth.useAuth, APPLICANT);
    mockHttp({ "licensing-requests": "pending" });
    const { container } = renderPage(<LicensingPage />);
    expect(hasLoader(container)).toBe(true);
  });

  it("shows an empty state", async () => {
    authAs(auth.useAuth, APPLICANT);
    mockHttp({ "licensing-requests": [] });
    renderPage(<LicensingPage />);
    expect(await screen.findByText("No licensing requests")).toBeInTheDocument();
  });

  it("shows the server's message when loading fails", async () => {
    authAs(auth.useAuth, APPLICANT);
    mockHttp({ "licensing-requests": serverError(500, "Licensing unavailable.") });
    renderPage(<LicensingPage />);
    expect(await screen.findByText("Licensing unavailable.")).toBeInTheDocument();
  });

  it("gives an applicant no negotiation controls", async () => {
    authAs(auth.useAuth, APPLICANT);
    mockHttp({ "licensing-requests": [REQ] });
    renderPage(<LicensingPage />);
    expect(await screen.findByText("TTC")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Add note" })).toBeNull();
  });

  it("records a negotiation note as PCC_ADMIN", async () => {
    authAs(auth.useAuth, ["pms.licensing_request.view", "pms.licensing_request.review"], 4001);
    const calls = mockHttp({ "licensing-requests": [REQ] },
      { "licensing-requests/3/notes": serverError(409, "Not routed yet.") });
    renderPage(<LicensingPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Add note" }));
    await userEvent.type(screen.getByRole("textbox", { name: "Note" }), "Term sheet in.");
    await userEvent.click(screen.getByRole("button", { name: "Add" }));
    await waitFor(() => expect(calls.post).toHaveBeenCalledWith(
      "/pms/licensing-requests/3/notes", { note: "Term sheet in." }));
    expect(await screen.findByText("Not routed yet.")).toBeInTheDocument();
  });
});
