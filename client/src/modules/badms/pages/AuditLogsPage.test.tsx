import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AuditEvent } from "../api/types";
import AuditLogsPage from "./AuditLogsPage";

const hooks = vi.hoisted(() => ({
  useAuditLogs: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const sampleAudit: AuditEvent = {
  id: 1,
  event_type: "manual_backup_triggered",
  actor_user_id: 1,
  actor_role: "Super Admin",
  target_model: "BackupRecord",
  target_id: 101,
  department: "Institute",
  details: { dataset: "fusion_integrated" },
  ip_address: "127.0.0.1",
  timestamp: "2026-11-22T02:00:00Z",
};

describe("AuditLogsPage", () => {
  beforeEach(() => {
    hooks.useAuditLogs.mockReturnValue({
      data: { results: [sampleAudit] },
      isPending: false,
      error: null,
    });
  });

  it("renders audit log table with events", () => {
    render(
      <MantineProvider>
        <AuditLogsPage />
      </MantineProvider>
    );

    expect(screen.getByText("BADMS Audit Logs")).toBeInTheDocument();
    expect(screen.getByText("manual_backup_triggered")).toBeInTheDocument();
    expect(screen.getByText("BackupRecord #101")).toBeInTheDocument();
  });
});
