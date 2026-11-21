import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DashboardPage from "./DashboardPage";

const hooks = vi.hoisted(() => ({
  useDashboard: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

describe("DashboardPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders loader while pending", () => {
    hooks.useDashboard.mockReturnValue({
      data: null,
      isPending: true,
      error: null,
    });

    const { container } = render(
      <MantineProvider>
        <DashboardPage />
      </MantineProvider>,
    );
    expect(container.querySelector(".mantine-Loader-root")).toBeInTheDocument();
  });

  it("renders error state on 500 failure", () => {
    hooks.useDashboard.mockReturnValue({
      data: null,
      isPending: false,
      error: new Error("Server error 500"),
    });

    render(
      <MantineProvider>
        <DashboardPage />
      </MantineProvider>,
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("Could not load this")).toBeInTheDocument();
  });

  it("renders metrics when loaded successfully", () => {
    hooks.useDashboard.mockReturnValue({
      data: {
        archived_users_total: 42,
        archived_users_reversible: 5,
        purge_requests_pending: 3,
        audit_logs_total: 120,
      },
      isPending: false,
      error: null,
    });

    render(
      <MantineProvider>
        <DashboardPage />
      </MantineProvider>,
    );

    expect(screen.getByRole("heading", { name: "System Administration" })).toBeInTheDocument();
    expect(screen.getByText("Archived Users")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("Pending Purges")).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("Reversible Users")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("Total Audit Events")).toBeInTheDocument();
    expect(screen.getByText("120")).toBeInTheDocument();
  });
});
