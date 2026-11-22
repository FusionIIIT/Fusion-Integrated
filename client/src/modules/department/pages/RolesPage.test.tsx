import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import RolesPage from "./RolesPage";
import { api, page, renderPage, serverError, setup } from "./testUtils";

vi.mock("../../../lib/http", async (orig) => (await import("./testUtils")).httpMock(orig));
vi.mock("../../../auth/AuthProvider", async () => (await import("./testUtils")).authMock());

const TENURE = { id: 1, department: "CSE", role: "hod", user_id: 49, valid_from: "2026-01-01T00:00:00Z",
  valid_to: "2029-01-01T00:00:00Z", assigned_by: 5, transition_applied_at: null, in_effect: true };

describe("RolesPage", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows loading", () => {
    setup([], { "/role-assignments": "pending" });
    renderPage(<RolesPage />);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("shows an empty state", async () => {
    setup([], { "/role-assignments": page([]), "/departments": [] });
    renderPage(<RolesPage />);
    expect(await screen.findByText("No HOD or Dept_Admin tenure recorded")).toBeInTheDocument();
  });

  it("shows the error message", async () => {
    setup([], { "/role-assignments": serverError(), "/departments": [] });
    renderPage(<RolesPage />);
    expect(await screen.findByText("Server exploded.")).toBeInTheDocument();
  });

  it("names each vacant or ending role", async () => {
    setup(["department.role_assignment.view"], { "/role-assignments": page([TENURE]), "/departments": [],
      "/role-assignments/vacancies": [{ department: "SM", role: "hod", problem: "vacant",
        message: "SM has no HOD in effect." }] });
    renderPage(<RolesPage />);
    expect(await screen.findByText("SM has no HOD in effect.")).toBeInTheDocument();
  });

  it("gives the HOD a read-only view", async () => {
    setup(["department.role_assignment.view"], { "/role-assignments": page([TENURE]), "/departments": [] });
    renderPage(<RolesPage />);
    expect(await screen.findByText("in effect")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Record tenure" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Change end" })).toBeNull();
  });

  it("lets the central authority change an end date and shows a refusal", async () => {
    setup(["department.role_assignment.view", "department.role_assignment.assign"],
      { "/role-assignments": page([TENURE]), "/departments": [] }, "central");
    api.patch.mockRejectedValueOnce(serverError("Record the successor first.", 422));
    renderPage(<RolesPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Change end" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("New end"), { target: { value: "2027-01-01T10:00" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    expect(await screen.findByText("Record the successor first.")).toBeInTheDocument();
    await waitFor(() => expect(api.patch).toHaveBeenCalledWith("/department/role-assignments/1",
      { valid_to: new Date("2027-01-01T10:00").toISOString() }));
  });

  it("shows the owning office no control its permissions do not allow", async () => {
    setup(["department.role_assignment.view"], { "/role-assignments": page([TENURE]), "/departments": [] }, "central");
    renderPage(<RolesPage />);
    expect(await screen.findByText("in effect")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Record tenure" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Change end" })).toBeNull();
  });
});
