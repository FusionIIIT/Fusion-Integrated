import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { BackupSchedule } from "../api/types";
import SchedulesPage from "./SchedulesPage";

const hooks = vi.hoisted(() => ({
  useBackupSchedules: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const sampleSchedule: BackupSchedule = {
  id: 1,
  name: "Nightly Global DB Dump",
  scope_type: "global",
  dataset_name: "fusion_integrated",
  cron_expression: "0 2 * * *",
  data_classification_filter: "Critical",
  is_active: true,
  created_by_user_id: 1,
  version: 1,
  effective_from: "2026-11-01T00:00:00Z",
  effective_to: null,
  last_run_at: "2026-11-21T02:00:00Z",
  next_run_at: "2026-11-22T02:00:00Z",
  created_at: "2026-11-01T00:00:00Z",
};

describe("SchedulesPage", () => {
  beforeEach(() => {
    hooks.useBackupSchedules.mockReturnValue({
      data: { results: [sampleSchedule] },
      isPending: false,
      error: null,
    });
  });

  it("renders backup schedule cards with cron expression", () => {
    render(
      <MantineProvider>
        <SchedulesPage />
      </MantineProvider>
    );

    expect(screen.getByText("Backup Schedules")).toBeInTheDocument();
    expect(screen.getByText("Nightly Global DB Dump")).toBeInTheDocument();
    expect(screen.getByText("0 2 * * *")).toBeInTheDocument();
  });
});
