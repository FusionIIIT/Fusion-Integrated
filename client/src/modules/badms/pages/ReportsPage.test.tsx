import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { DepartmentReport } from "../api/types";
import ReportsPage from "./ReportsPage";

const hooks = vi.hoisted(() => ({
  useDepartmentReport: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const sampleReport: DepartmentReport = {
  department: "CSE",
  total_archival_requests: 12,
  archival_by_status: { approved: 8, submitted: 4 },
  total_storage_extensions: 5,
  storage_by_status: { approved: 3, submitted: 2 },
};

describe("ReportsPage", () => {
  beforeEach(() => {
    hooks.useDepartmentReport.mockReturnValue({
      data: sampleReport,
      isPending: false,
      error: null,
    });
  });

  it("renders report metric cards", () => {
    render(
      <MantineProvider>
        <ReportsPage />
      </MantineProvider>
    );

    expect(screen.getByText("BADMS Reports")).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("8")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
  });
});
