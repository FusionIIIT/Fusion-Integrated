import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { HistoricalArchive } from "../api/types";
import ArchivePage from "./ArchivePage";

const hooks = vi.hoisted(() => ({
  useArchives: vi.fn(),
  useCreateArchive: vi.fn(),
  useRestoreArchive: vi.fn(),
  useRequestPurge: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const sampleArchive: HistoricalArchive = {
  id: 1,
  entity_type: "EXAM_RECORDS",
  record_identifier: "2020_SPRING",
  payload: { batch: "2020" },
  backup_reference: "s3://backups/2020_spring.tar.gz",
  retention_period_days: 1825,
  purge_eligible_at: "2025-05-01T00:00:00Z",
  status: "ARCHIVED",
  archived_by_user_id: 1,
  created_at: "2020-05-01T00:00:00Z",
};

describe("ArchivePage", () => {
  beforeEach(() => {
    const idle = { mutate: vi.fn(), isPending: false };
    hooks.useArchives.mockReturnValue({
      data: [sampleArchive],
      isLoading: false,
      isError: false,
    });
    hooks.useCreateArchive.mockReturnValue(idle);
    hooks.useRestoreArchive.mockReturnValue(idle);
    hooks.useRequestPurge.mockReturnValue(idle);
  });

  it("renders archive records", () => {
    render(
      <MantineProvider>
        <ArchivePage />
      </MantineProvider>
    );

    expect(screen.getByText("Historical Archive Records")).toBeInTheDocument();
    expect(screen.getByText("EXAM_RECORDS")).toBeInTheDocument();
    expect(screen.getByText("2020_SPRING")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Request Purge" })).toBeInTheDocument();
  });
});
