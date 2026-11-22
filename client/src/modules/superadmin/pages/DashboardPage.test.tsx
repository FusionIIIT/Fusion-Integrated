import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DashboardPage from "./DashboardPage";

const hooks = vi.hoisted(() => ({
  useDashboardMetrics: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

describe("DashboardPage", () => {
  beforeEach(() => {
    hooks.useDashboardMetrics.mockReturnValue({
      data: {
        total_users: 1500,
        active_users: 1420,
        deactivated_users: 50,
        archived_reversible_users: 25,
        archived_permanent_users: 5,
      },
      isLoading: false,
      isError: false,
    });
  });

  it("renders administrative metrics cards", () => {
    render(
      <MantineProvider>
        <DashboardPage />
      </MantineProvider>
    );

    expect(screen.getByText("Super Admin Dashboard")).toBeInTheDocument();
    expect(screen.getByText("Total Users")).toBeInTheDocument();
    expect(screen.getByText("1500")).toBeInTheDocument();
    expect(screen.getByText("Active Users")).toBeInTheDocument();
    expect(screen.getByText("1420")).toBeInTheDocument();
  });
});
