import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ArchivedUser } from "../api/types";
import ArchivalPage from "./ArchivalPage";

const hooks = vi.hoisted(() => ({
  useArchivedUsers: vi.fn(),
  useRestoreUser: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const reversibleUser: ArchivedUser = {
  user_id: 101,
  institute_id: "2021001",
  username: "stu001",
  email: "stu001@iiitdmj.ac.in",
  user_kind: "student",
  status: "reversible",
  archived_at: "2026-11-01T10:00:00Z",
  reversible_until: "2026-12-01T10:00:00Z",
  authorized_by: 1,
  archival_reason: "Graduated",
  restored_at: null,
  restored_by: null,
  restoration_reason: "",
  finalized_permanent_at: null,
  created_at: "2026-11-01T10:00:00Z",
  updated_at: "2026-11-01T10:00:00Z",
};

const permanentUser: ArchivedUser = {
  ...reversibleUser,
  user_id: 102,
  username: "stu002",
  status: "finalized_permanent",
};

describe("ArchivalPage", () => {
  const mockRestore = { mutate: vi.fn(), isPending: false };

  beforeEach(() => {
    vi.restoreAllMocks();
    mockRestore.mutate.mockReset();
    hooks.useRestoreUser.mockReturnValue(mockRestore);
  });

  it("renders loader during loading state", () => {
    hooks.useArchivedUsers.mockReturnValue({
      data: null,
      isPending: true,
      error: null,
    });

    const { container } = render(
      <MantineProvider>
        <ArchivalPage />
      </MantineProvider>,
    );
    expect(container.querySelector(".mantine-Loader-root")).toBeInTheDocument();
  });

  it("renders empty state placeholder when no records exist", () => {
    hooks.useArchivedUsers.mockReturnValue({
      data: { count: 0, next: null, previous: null, results: [] },
      isPending: false,
      error: null,
    });

    render(
      <MantineProvider>
        <ArchivalPage />
      </MantineProvider>,
    );
    expect(screen.getByText("No archived users")).toBeInTheDocument();
  });

  it("renders error state on 500 error", () => {
    hooks.useArchivedUsers.mockReturnValue({
      data: null,
      isPending: false,
      error: new Error("Failed to fetch archival records"),
    });

    render(
      <MantineProvider>
        <ArchivalPage />
      </MantineProvider>,
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("Could not load this")).toBeInTheDocument();
  });

  it("hides restore action control for permanently finalized users", () => {
    hooks.useArchivedUsers.mockReturnValue({
      data: { count: 1, next: null, previous: null, results: [permanentUser] },
      isPending: false,
      error: null,
    });

    render(
      <MantineProvider>
        <ArchivalPage />
      </MantineProvider>,
    );
    expect(screen.getByText("stu002")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /restore/i })).toBeNull();
  });

  it("renders restore action for reversible users and triggers restore mutation", async () => {
    hooks.useArchivedUsers.mockReturnValue({
      data: { count: 1, next: null, previous: null, results: [reversibleUser] },
      isPending: false,
      error: null,
    });

    render(
      <MantineProvider>
        <ArchivalPage />
      </MantineProvider>,
    );

    const restoreBtn = await screen.findByRole("button", { name: /restore/i });
    expect(restoreBtn).toBeInTheDocument();
    fireEvent.click(restoreBtn);

    const dialog = await screen.findByRole("dialog");
    const textarea = within(dialog).getByLabelText(/^Restoration reason/i);
    fireEvent.change(textarea, { target: { value: "Re-enrolled student" } });

    fireEvent.click(within(dialog).getByRole("button", { name: "Confirm Restore" }));

    expect(mockRestore.mutate).toHaveBeenCalledWith(
      { user_id: 101, restoration_reason: "Re-enrolled student" },
      expect.any(Object),
    );
  });
});
