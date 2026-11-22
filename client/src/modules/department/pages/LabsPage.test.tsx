import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import LabsPage from "./LabsPage";
import { api, page, renderPage, serverError, setup } from "./testUtils";

vi.mock("../../../lib/http", async (orig) => (await import("./testUtils")).httpMock(orig));
vi.mock("../../../auth/AuthProvider", async () => (await import("./testUtils")).authMock());

const LAB = { id: 1, name: "IoT Lab", location: "C", equipment: "Kits", capacity: 30, status: "available",
  updated_at: "2026-11-22" };

describe("LabsPage", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows loading", () => {
    setup([], { "/lab-resources": "pending" });
    renderPage(<LabsPage />);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("shows an empty state", async () => {
    setup([], { "/lab-resources": page([]) });
    renderPage(<LabsPage />);
    expect(await screen.findByText("No lab resources recorded yet")).toBeInTheDocument();
  });

  it("shows the error message", async () => {
    setup([], { "/lab-resources": serverError() });
    renderPage(<LabsPage />);
    expect(await screen.findByText("Server exploded.")).toBeInTheDocument();
  });

  it("gives faculty a read-only view", async () => {
    setup(["department.lab_resource.view"], { "/lab-resources": page([LAB]) });
    renderPage(<LabsPage />);
    expect(await screen.findByText("IoT Lab")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit" })).toBeNull();
  });

  it("lets Dept_Admin add a lab and shows a refusal", async () => {
    setup(["department.lab_resource.view", "department.lab_resource.update"], { "/lab-resources": page([]) }, "dept_admin");
    api.post.mockRejectedValueOnce(serverError("Give the lab or resource a name.", 422));
    renderPage(<LabsPage />);
    fireEvent.click(await screen.findByRole("button", { name: "Add lab" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    expect(await screen.findByText("Give the lab or resource a name.")).toBeInTheDocument();
    await waitFor(() => expect(api.post).toHaveBeenCalledWith("/department/lab-resources",
      expect.objectContaining({ name: "", status: "available" })));
  });
});
