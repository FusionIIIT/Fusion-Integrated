import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { authAs, hasLoader, mockHttp, renderPage, serverError } from "../test-utils";
import AttorneyPanelPage from "./AttorneyPanelPage";

const auth = vi.hoisted(() => ({ useAuth: vi.fn() }));
vi.mock("../../../auth/AuthProvider", () => auth);

const PERMS = ["pms.attorney_panel.update"];
const ENTRY = { id: 3, user_id: 2001, name: "Dr Rao", domain_codes: ["materials"],
  valid_from: "2026-11-01", valid_to: null, workload: 2 };

describe("AttorneyPanelPage", () => {
  afterEach(() => vi.restoreAllMocks());

  it("shows a spinner while loading", () => {
    authAs(auth.useAuth, PERMS);
    mockHttp({ "attorney-panel": "pending" });
    const { container } = renderPage(<AttorneyPanelPage />);
    expect(hasLoader(container)).toBe(true);
  });

  it("shows an empty state", async () => {
    authAs(auth.useAuth, PERMS);
    mockHttp({ "attorney-panel": [] });
    renderPage(<AttorneyPanelPage />);
    expect(await screen.findByText("No panel attorneys yet")).toBeInTheDocument();
  });

  it("shows the server's message when loading fails", async () => {
    authAs(auth.useAuth, PERMS);
    mockHttp({ "attorney-panel": serverError(500, "Roster unavailable.") });
    renderPage(<AttorneyPanelPage />);
    expect(await screen.findByText("Roster unavailable.")).toBeInTheDocument();
  });

  it("lists the roster with each person's workload", async () => {
    authAs(auth.useAuth, PERMS);
    mockHttp({ "attorney-panel": [ENTRY] });
    renderPage(<AttorneyPanelPage />);
    expect(await screen.findByText("Dr Rao")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("removes someone from the roster", async () => {
    authAs(auth.useAuth, PERMS);
    const calls = mockHttp({ "attorney-panel": [ENTRY] },
      { "attorney-panel/3/end": serverError(409, "This person has already left the roster.") });
    renderPage(<AttorneyPanelPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Remove" }));
    const buttons = screen.getAllByRole("button", { name: "Remove" });
    await userEvent.click(buttons[buttons.length - 1] as HTMLElement);
    await waitFor(() => expect(calls.post).toHaveBeenCalledWith("/pms/attorney-panel/3/end", {}));
    expect(await screen.findByText("This person has already left the roster.")).toBeInTheDocument();
  });
});
