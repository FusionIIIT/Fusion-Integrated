import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ArchivedUser, HistoricalArchive } from "../api/types";
import ArchivalPage from "./ArchivalPage";

const hooks = vi.hoisted(() => ({
  useArchivedUsers: vi.fn(),
  useArchiveUser: vi.fn(),
  useRestoreUser: vi.fn(),
  useHistoricalArchives: vi.fn(),
  useCreateHistoricalArchive: vi.fn(),
  useRestoreHistoricalArchive: vi.fn(),
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

const sampleArchive: HistoricalArchive = {
  id: 11,
  dataset_category: "academics",
  title: "Legacy Grades 2019",
  date_range_start: "2019-01-01",
  date_range_end: "2019-12-31",
  record_count: 120,
  backup_file_path: "/backups/grades_2019.tar.gz",
  backup_checksum: "a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90",
  retention_expires_at: "2027-01-01",
  is_restored: false,
  restored_at: null,
  is_purged: false,
  archived_by: 1,
  created_at: "2026-11-01T10:00:00Z",
  updated_at: "2026-11-01T10:00:00Z",
};

describe("ArchivalPage", () => {
  const mockRestore = { mutate: vi.fn(), isPending: false };
  const mockArchiveUser = { mutate: vi.fn(), isPending: false };
  const mockCreateDataset = { mutate: vi.fn(), isPending: false };
  const mockRestoreDataset = { mutate: vi.fn(), isPending: false };

  beforeEach(() => {
    vi.restoreAllMocks();
    mockRestore.mutate.mockReset();
    mockArchiveUser.mutate.mockReset();
    mockCreateDataset.mutate.mockReset();
    mockRestoreDataset.mutate.mockReset();
    hooks.useRestoreUser.mockReturnValue(mockRestore);
    hooks.useArchiveUser.mockReturnValue(mockArchiveUser);
    hooks.useCreateHistoricalArchive.mockReturnValue(mockCreateDataset);
    hooks.useRestoreHistoricalArchive.mockReturnValue(mockRestoreDataset);
    hooks.useHistoricalArchives.mockReturnValue({
      data: { count: 0, next: null, previous: null, results: [] },
      isPending: false,
      error: null,
    });
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
    expect(screen.queryByRole("button", { name: /^Restore$/i })).toBeNull();
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

    const restoreBtn = await screen.findByRole("button", { name: /^Restore$/i });
    expect(restoreBtn).toBeInTheDocument();
    fireEvent.click(restoreBtn);

    const dialog = await screen.findByRole("dialog");
    const textarea = within(dialog).getByLabelText(/^Restoration reason/i);
    fireEvent.change(textarea, { target: { value: "Re-enrolled student" } });

    const confirmBtn = within(dialog).getByRole("button", { name: /Confirm Restore/i });
    fireEvent.click(confirmBtn);

    expect(mockRestore.mutate).toHaveBeenCalledWith(
      { user_id: 101, restoration_reason: "Re-enrolled student" },
      expect.any(Object),
    );
  });

  it("submits archive user modal through UI controls", async () => {
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

    fireEvent.click(screen.getByRole("button", { name: /Archive User/i }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText(/^Institute ID/i), { target: { value: "2021BCS901" } });
    fireEvent.change(within(dialog).getByLabelText(/^Username/i), { target: { value: "stu901" } });
    fireEvent.change(within(dialog).getByLabelText(/^Institute Email/i), {
      target: { value: "stu901@iiitdmj.ac.in" },
    });
    fireEvent.change(within(dialog).getByLabelText(/^Archival reason/i), {
      target: { value: "Completed degree" },
    });

    fireEvent.click(within(dialog).getByRole("button", { name: /Confirm Archive User/i }));
    expect(mockArchiveUser.mutate).toHaveBeenCalledWith(
      expect.objectContaining({
        institute_id: "2021BCS901",
        username: "stu901",
        email: "stu901@iiitdmj.ac.in",
        archival_reason: "Completed degree",
      }),
      expect.any(Object),
    );
  });

  it("creates and restores historical dataset archives through UI controls", async () => {
    hooks.useArchivedUsers.mockReturnValue({
      data: { count: 0, next: null, previous: null, results: [] },
      isPending: false,
      error: null,
    });
    hooks.useHistoricalArchives.mockReturnValue({
      data: { count: 1, next: null, previous: null, results: [sampleArchive] },
      isPending: false,
      error: null,
    });

    render(
      <MantineProvider>
        <ArchivalPage />
      </MantineProvider>,
    );

    expect(screen.getByText("Legacy Grades 2019")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Restore Dataset/i }));
    expect(mockRestoreDataset.mutate).toHaveBeenCalledWith(11, expect.any(Object));

    fireEvent.click(screen.getByRole("button", { name: /Archive Dataset/i }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.change(within(dialog).getByLabelText(/^Dataset title/i), {
      target: { value: "Finance Ledger 2018" },
    });
    fireEvent.click(within(dialog).getByRole("button", { name: /Confirm Archive Dataset/i }));
    expect(mockCreateDataset.mutate).toHaveBeenCalledWith(
      expect.objectContaining({ title: "Finance Ledger 2018" }),
      expect.any(Object),
    );
  });
});
