import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ProjectsListPage from "./ProjectsListPage";
import type { Project } from "../api/types";

const hooks = vi.hoisted(() => ({
  useProjects: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const fakeProject: Project = {
  id: 1,
  project_code: "RSPC/2026/CSE/001",
  project_type: "sponsored",
  title: "Cloud Cryptography Grant",
  user_id: 10,
  department: "CSE",
  funding_agency: "DST",
  sanction_order_no: "DST-2026-99",
  sanction_date: "2026-01-15",
  start_date: "2026-02-01",
  end_date: "2028-01-31",
  sanctioned_amount: "1500000.00",
  status: "active",
  created_at: "2026-02-01T00:00:00Z",
  updated_at: "2026-02-01T00:00:00Z",
};

describe("ProjectsListPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("1. renders loading state while projects are fetching", () => {
    hooks.useProjects.mockReturnValue({
      data: undefined,
      isLoading: true,
      error: null,
    });

    render(
      <MantineProvider>
        <ProjectsListPage />
      </MantineProvider>
    );

    expect(screen.getByText("Loading projects...")).toBeInTheDocument();
  });

  it("2. renders empty state when no projects are returned", () => {
    hooks.useProjects.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    });

    render(
      <MantineProvider>
        <ProjectsListPage />
      </MantineProvider>
    );

    expect(
      screen.getByText("No active or sanctioned projects found.")
    ).toBeInTheDocument();
  });

  it("3. renders error banner on API rejection", () => {
    hooks.useProjects.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: { response: { data: { error: { message: "Permission denied for projects" } } } },
    });

    render(
      <MantineProvider>
        <ProjectsListPage />
      </MantineProvider>
    );

    expect(screen.getByText("Could not load this")).toBeInTheDocument();
    expect(screen.getByText("Permission denied for projects")).toBeInTheDocument();
  });

  it("4. renders project items and status badge when data is present", () => {
    hooks.useProjects.mockReturnValue({
      data: [fakeProject],
      isLoading: false,
      error: null,
    });

    render(
      <MantineProvider>
        <ProjectsListPage />
      </MantineProvider>
    );

    expect(screen.getByText("RSPC/2026/CSE/001")).toBeInTheDocument();
    expect(screen.getByText("Cloud Cryptography Grant")).toBeInTheDocument();
    expect(screen.getByText("active")).toBeInTheDocument();
  });
});
