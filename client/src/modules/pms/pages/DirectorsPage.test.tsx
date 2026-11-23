import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { authAs, hasLoader, mockHttp, renderPage, serverError } from "../test-utils";
import DirectorsPage from "./DirectorsPage";

const auth = vi.hoisted(() => ({ useAuth: vi.fn() }));
vi.mock("../../../auth/AuthProvider", () => auth);

const PERMS = ["pms.director_profile.update"];
const ENTRY = { id: 3, user_id: 2001, name: "Dr Rao", domain_codes: ["materials"],
  valid_from: "2026-11-01", valid_to: null, workload: 2 };

describe("DirectorsPage", () => {
  afterEach(() => vi.restoreAllMocks());

  it("shows a spinner while loading", () => {
    authAs(auth.useAuth, PERMS);
    mockHttp({ "directors": "pending" });
    const { container } = renderPage(<DirectorsPage />);
    expect(hasLoader(container)).toBe(true);
  });

  it("shows an empty state", async () => {
    authAs(auth.useAuth, PERMS);
    mockHttp({ "directors": [] });
    renderPage(<DirectorsPage />);
    expect(await screen.findByText("No Directors yet")).toBeInTheDocument();
  });

  it("shows the server's message when loading fails", async () => {
    authAs(auth.useAuth, PERMS);
    mockHttp({ "directors": serverError(500, "Roster unavailable.") });
    renderPage(<DirectorsPage />);
    expect(await screen.findByText("Roster unavailable.")).toBeInTheDocument();
  });

  it("lists the roster with each person's workload", async () => {
    authAs(auth.useAuth, PERMS);
    mockHttp({ "directors": [ENTRY] });
    renderPage(<DirectorsPage />);
    expect(await screen.findByText("Dr Rao")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("removes someone from the roster", async () => {
    authAs(auth.useAuth, PERMS);
    const calls = mockHttp({ "directors": [ENTRY] },
      { "directors/3/end": serverError(409, "This person has already left the roster.") });
    renderPage(<DirectorsPage />);
    await userEvent.click(await screen.findByRole("button", { name: "Remove" }));
    const buttons = screen.getAllByRole("button", { name: "Remove" });
    await userEvent.click(buttons[buttons.length - 1] as HTMLElement);
    await waitFor(() => expect(calls.post).toHaveBeenCalledWith("/pms/directors/3/end", {}));
    expect(await screen.findByText("This person has already left the roster.")).toBeInTheDocument();
  });
});
