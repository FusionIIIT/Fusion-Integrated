import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ProfilesPage from "./ProfilesPage";
import { api, page, renderPage, serverError, setup } from "./testUtils";

vi.mock("../../../lib/http", async (orig) => (await import("./testUtils")).httpMock(orig));
vi.mock("../../../auth/AuthProvider", async () => (await import("./testUtils")).authMock());

const BASIC = { tier: "basic", id: 9, kind: "faculty", display_name: "A. Rao", programme: "", department: "CSE" };

describe("ProfilesPage", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows loading", () => {
    setup([], { "/profiles": "pending" });
    renderPage(<ProfilesPage />);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("shows an empty state", async () => {
    setup([], { "/profiles": page([]) });
    renderPage(<ProfilesPage />);
    expect(await screen.findByText("No department profiles yet")).toBeInTheDocument();
  });

  it("shows the error message", async () => {
    setup([], { "/profiles": serverError() });
    renderPage(<ProfilesPage />);
    expect(await screen.findByText("Server exploded.")).toBeInTheDocument();
  });

  it("shows a student only the basic tier and no management", async () => {
    setup(["department.profile.view"], { "/profiles": page([BASIC]) });
    renderPage(<ProfilesPage />);
    expect(await screen.findByText("A. Rao")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Add profile" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Deactivate" })).toBeNull();
  });

  it("lets Dept_Admin add an alumni profile and shows a refusal", async () => {
    setup(["department.profile.view", "department.profile.update"], { "/profiles": page([]) }, "dept_admin");
    api.post.mockRejectedValueOnce(serverError("Give the profile a name.", 422));
    renderPage(<ProfilesPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Add profile" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    expect(await screen.findByText("Give the profile a name.")).toBeInTheDocument();
    await waitFor(() => expect(api.post).toHaveBeenCalledWith("/department/profiles",
      expect.objectContaining({ kind: "faculty", user_id: null })));
  });
});
