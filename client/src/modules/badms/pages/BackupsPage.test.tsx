import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { BackupRecord } from "../api/types";
import { RequirePermission } from "../../../auth/RequirePermission";
import BackupsPage from "./BackupsPage";

const authMock = vi.hoisted(() => ({
  useAuth: vi.fn(),
}));
vi.mock("../../../auth/AuthProvider", () => authMock);

const hooks = vi.hoisted(() => ({
  useBackups: vi.fn(),
  useTriggerManualBackup: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const sampleBackup: BackupRecord = {
  id: 1,
  backup_type: "manual",
  dataset_name: "fusion_integrated",
  status: "success",
  started_at: "2026-11-22T02:00:00Z",
  completed_at: "2026-11-22T02:05:00Z",
  file_path: "/data/backups/dump.dump",
  file_size_bytes: 1048576,
  checksum_sha256: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  error_message: "",
  triggered_by_user_id: 1,
  consecutive_failure_count: 0,
  created_at: "2026-11-22T02:00:00Z",
};

describe("BackupsPage", () => {
  const triggerMutate = vi.fn();

  beforeEach(() => {
    authMock.useAuth.mockReturnValue({
      can: (perm: string) => perm === "badms.backup.manage",
    });
    hooks.useBackups.mockReturnValue({
      data: { results: [sampleBackup] },
      isPending: false,
      error: null,
    });
    hooks.useTriggerManualBackup.mockReturnValue({
      mutate: triggerMutate,
      isPending: false,
    });
  });

  it("renders backup list and allows authorized user to trigger backup", () => {
    render(
      <MantineProvider>
        <BackupsPage />
      </MantineProvider>
    );

    expect(screen.getByText("Database Backups")).toBeInTheDocument();
    expect(screen.getByText("fusion_integrated")).toBeInTheDocument();

    const triggerBtn = screen.getByRole("button", { name: /trigger manual backup/i });
    expect(triggerBtn).toBeInTheDocument();
    fireEvent.click(triggerBtn);
    expect(triggerMutate).toHaveBeenCalledWith("fusion_integrated", expect.any(Object));
  });

  it("hides trigger button when user lacks badms.backup.manage", () => {
    authMock.useAuth.mockReturnValue({
      can: () => false,
    });

    render(
      <MantineProvider>
        <BackupsPage />
      </MantineProvider>
    );

    expect(screen.queryByRole("button", { name: /trigger manual backup/i })).toBeNull();
  });

  it("renders empty state when no backups exist", () => {
    hooks.useBackups.mockReturnValue({
      data: { results: [] },
      isPending: false,
      error: null,
    });

    render(
      <MantineProvider>
        <BackupsPage />
      </MantineProvider>
    );

    expect(screen.getByText("No backup records found")).toBeInTheDocument();
  });

  it("shows Not available to your role when wrapped in RequirePermission for role lacking badms.backup.view", () => {
    authMock.useAuth.mockReturnValue({
      can: (perm: string) => perm !== "badms.backup.view",
    });

    render(
      <MantineProvider>
        <RequirePermission permission="badms.backup.view">
          <BackupsPage />
        </RequirePermission>
      </MantineProvider>
    );

    expect(screen.getByText("Not available to your role")).toBeInTheDocument();
    expect(screen.queryByText("Database Backups")).toBeNull();
  });
});
