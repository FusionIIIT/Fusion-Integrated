import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AuditLog } from "../api/types";
import AuditPage from "./AuditPage";

const hooks = vi.hoisted(() => ({
  useAuditLogs: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const sampleLog: AuditLog = {
  id: 1,
  event_type: "SECURITY_ALERT",
  actor_user_id: 1,
  target_entity: "USER",
  target_id: "501",
  ip_address: "127.0.0.1",
  action_details: { alert: "Failed login threshold exceeded" },
  is_immutable: true,
  created_at: "2026-11-20T10:00:00Z",
};

describe("AuditPage", () => {
  beforeEach(() => {
    hooks.useAuditLogs.mockReturnValue({
      data: [sampleLog],
      isLoading: false,
      isError: false,
    });
  });

  it("renders immutable audit logs", () => {
    render(
      <MantineProvider>
        <AuditPage />
      </MantineProvider>
    );

    expect(screen.getByText("Audit Logs")).toBeInTheDocument();
    expect(screen.getByText("SECURITY_ALERT")).toBeInTheDocument();
    expect(screen.getByText("127.0.0.1")).toBeInTheDocument();
  });
});
