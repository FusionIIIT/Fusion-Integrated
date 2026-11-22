import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { FileAuditLog, UsageMetrics } from "../api/types";
import GovernancePage from "./GovernancePage";

const hooks = vi.hoisted(() => ({
  useGovernanceUsage: vi.fn(),
  useGovernanceAuditLogs: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const sampleMetrics: UsageMetrics = {
  total_files: 42,
  circulated_files: 15,
  draft_files: 7,
  archived_files: 20,
  discarded_drafts: 3,
  total_movements: 88,
};

const sampleLog: FileAuditLog = {
  id: 101,
  file_id: 1,
  action: "FILE_FORWARDED",
  actor_user_id: 10,
  actor_username: "prof_smith",
  actor_role: "Professor",
  details: { to_user_id: 20 },
  timestamp: "2026-11-20T12:00:00Z",
};

describe("GovernancePage", () => {
  beforeEach(() => {
    hooks.useGovernanceUsage.mockReturnValue({
      data: sampleMetrics,
      isPending: false,
      error: null,
    });
    hooks.useGovernanceAuditLogs.mockReturnValue({
      data: [sampleLog],
      isPending: false,
      error: null,
    });
  });

  it("renders governance metrics cards and audit trail", () => {
    render(
      <MantineProvider>
        <MemoryRouter>
          <GovernancePage />
        </MemoryRouter>
      </MantineProvider>,
    );

    expect(screen.getByText("FTS Governance & Audit")).toBeInTheDocument();
    expect(screen.getByText("Total Files")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("Active (Circulated)")).toBeInTheDocument();
    expect(screen.getByText("15")).toBeInTheDocument();
    expect(screen.getByText("FILE_FORWARDED")).toBeInTheDocument();
    expect(screen.getByText(/prof_smith/i)).toBeInTheDocument();
  });

  it("renders error state when metrics hook fails", () => {
    hooks.useGovernanceUsage.mockReturnValue({
      data: null,
      isPending: false,
      error: new Error("Governance metrics unavailable"),
    });

    render(
      <MantineProvider>
        <MemoryRouter>
          <GovernancePage />
        </MemoryRouter>
      </MantineProvider>,
    );

    expect(screen.getByText("Could not load this")).toBeInTheDocument();
  });

  it("shows placeholder when metrics are loading", () => {
    hooks.useGovernanceUsage.mockReturnValue({
      data: null,
      isPending: true,
      error: null,
    });

    render(
      <MantineProvider>
        <MemoryRouter>
          <GovernancePage />
        </MemoryRouter>
      </MantineProvider>,
    );

    const placeholders = screen.getAllByText("…");
    expect(placeholders.length).toBeGreaterThan(0);
  });
});
