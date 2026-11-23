import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import OverviewPage from "./OverviewPage";
import { api, page, renderPage, serverError, setup } from "./testUtils";

vi.mock("../../../lib/http", async (orig) => (await import("./testUtils")).httpMock(orig));
vi.mock("../../../auth/AuthProvider", async () => (await import("./testUtils")).authMock());

const DEPT = { id: 1, code: "CSE", name: "Computer Science and Engineering", core_policies: "", description: "",
  contact_email: "", contact_phone: "", office_location: "", website: "",
  headship: { user_id: 49, display_name: "Dr. Head" }, programmes: ["B.Tech"] };
const CHANGE = { id: 3, department: "CSE", field: "name", proposed_value: "Dept. of CSE", previous_value: "",
  status: "pending", proposed_by: 4, decided_by: null, decided_at: null, reason: "", created_at: "2026-11-22" };

describe("OverviewPage", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows loading", () => {
    setup([], { "/departments": "pending" });
    renderPage(<OverviewPage />);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("shows an empty state for someone with no department", async () => {
    setup([], { "/departments": [] });
    renderPage(<OverviewPage />);
    expect(await screen.findByText("You are not attached to a department in this role")).toBeInTheDocument();
  });

  it("shows the error message", async () => {
    setup([], { "/departments": serverError() });
    renderPage(<OverviewPage />);
    expect(await screen.findByText("Server exploded.")).toBeInTheDocument();
  });

  it("shows a student the headship and no edit controls", async () => {
    setup(["department.department.view"], { "/departments": [DEPT], "/departments/CSE": DEPT });
    renderPage(<OverviewPage />);
    expect(await screen.findByText("Dr. Head")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit details" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Propose official change" })).toBeNull();
  });

  it("lets Dept_Admin propose an official change and shows a refusal", async () => {
    setup(["department.department.view", "department.official_change.create", "department.official_change.view"],
      { "/departments": [DEPT], "/departments/CSE": DEPT, "/official-changes": page([]) }, "dept_admin");
    api.post.mockRejectedValueOnce(serverError("A change to name is already waiting for the HOD.", 409));
    renderPage(<OverviewPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Propose official change" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText("Proposed value"), { target: { value: "Dept. of CSE" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    expect(await screen.findByText(/already waiting for the HOD/)).toBeInTheDocument();
    expect(api.post).toHaveBeenCalledWith("/department/official-changes", { field: "name", value: "Dept. of CSE" });
  });

  it("lets the HOD approve a pending change", async () => {
    setup(["department.department.view", "department.official_change.view", "department.official_change.approve"],
      { "/departments": [DEPT], "/departments/CSE": DEPT, "/official-changes": page([CHANGE]) }, "hod");
    api.post.mockResolvedValue({ data: { ...CHANGE, status: "approved" } });
    renderPage(<OverviewPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Approve" }));
    await waitFor(() => expect(api.post).toHaveBeenCalledWith("/department/official-changes/3/decide",
      { approve: true }));
  });

  it("shows the owning office no control its permissions do not allow", async () => {
    setup(["department.department.view"], { "/departments": [DEPT], "/departments/CSE": DEPT }, "dept_admin");
    renderPage(<OverviewPage />);
    expect(await screen.findByText("Dr. Head")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit details" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Propose official change" })).toBeNull();
  });

  it("does not ask for official changes when the role cannot see them", async () => {
    setup(["department.department.view"], { "/departments": [DEPT], "/departments/CSE": DEPT }, "student");
    renderPage(<OverviewPage />);
    expect(await screen.findByText("Dr. Head")).toBeInTheDocument();
    expect(api.get.mock.calls.some(([url]) => String(url).endsWith("/official-changes"))).toBe(false);
  });

  it("shows the server's refusal when a decision fails", async () => {
    setup(["department.department.view", "department.official_change.view", "department.official_change.approve"],
      { "/departments": [DEPT], "/departments/CSE": DEPT, "/official-changes": page([CHANGE]) }, "hod");
    api.post.mockRejectedValueOnce(serverError("This change was already decided.", 409));
    renderPage(<OverviewPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Reject" }));
    expect(await screen.findByText("This change was already decided.")).toBeInTheDocument();
  });
});
