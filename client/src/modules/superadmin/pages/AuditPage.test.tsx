import { MantineProvider } from "@mantine/core";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { AuditLog } from "../api/types";
import AuditPage from "./AuditPage";

const hooks = vi.hoisted(() => ({
  useAuditLogs: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const sampleAudit: AuditLog = {
  id: 1,
  timestamp: "2026-11-01T12:00:00Z",
  actor_id: 10,
  actor_username: "sysadmin",
  actor_role: "super_admin",
  action: "purge.executed",
  target_id: "5",
  target_type: "HistoricalDataArchive",
  result: "SUCCESS",
  ip_address: "127.0.0.1",
  user_agent: "Mozilla/5.0",
  reason: "Retention period elapsed",
  context_metadata: {},
};

describe("AuditPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders loader during loading state", () => {
    hooks.useAuditLogs.mockReturnValue({
      data: null,
      isPending: true,
      error: null,
    });

    const { container } = render(
      <MantineProvider>
        <AuditPage />
      </MantineProvider>,
    );
    expect(container.querySelector(".mantine-Loader-root")).toBeInTheDocument();
  });

  it("renders empty state placeholder when no audit records exist", () => {
    hooks.useAuditLogs.mockReturnValue({
      data: { count: 0, next: null, previous: null, results: [] },
      isPending: false,
      error: null,
    });

    render(
      <MantineProvider>
        <AuditPage />
      </MantineProvider>,
    );
    expect(screen.getByText("No audit events found")).toBeInTheDocument();
  });

  it("renders error state on 500 error", () => {
    hooks.useAuditLogs.mockReturnValue({
      data: null,
      isPending: false,
      error: new Error("Audit service unavailable"),
    });

    render(
      <MantineProvider>
        <AuditPage />
      </MantineProvider>,
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("Could not load this")).toBeInTheDocument();
  });

  it("renders audit log records and filters by actor username", () => {
    hooks.useAuditLogs.mockReturnValue({
      data: { count: 1, next: null, previous: null, results: [sampleAudit] },
      isPending: false,
      error: null,
    });

    render(
      <MantineProvider>
        <AuditPage />
      </MantineProvider>,
    );

    expect(screen.getByRole("heading", { name: "Audit Logs" })).toBeInTheDocument();
    expect(screen.getByText("sysadmin")).toBeInTheDocument();
    expect(within(screen.getByRole("table")).getByText("purge.executed")).toBeInTheDocument();
    expect(screen.getByText("SUCCESS")).toBeInTheDocument();

    const searchInput = screen.getByPlaceholderText(/search by actor username/i);
    expect(searchInput).toBeInTheDocument();
    fireEvent.change(searchInput, { target: { value: "sysadmin" } });
    expect(hooks.useAuditLogs).toHaveBeenCalledWith(expect.objectContaining({ actor_username: "sysadmin" }));
  });
});
