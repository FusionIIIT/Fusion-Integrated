import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { RoleAssignment } from "../api/types";
import RolesPage from "./RolesPage";

const hooks = vi.hoisted(() => ({
  useRoles: vi.fn(),
  useAssignRole: vi.fn(),
  useExtendRole: vi.fn(),
  useRevokeRole: vi.fn(),
  useReassignRole: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const sampleRole: RoleAssignment = {
  id: 10,
  user_id: 201,
  role_name: "Course Instructor",
  scope_type: "COURSE",
  scope_id: "CS201",
  valid_from: "2026-08-01T00:00:00Z",
  valid_to: "2026-12-01T00:00:00Z",
  status: "ACTIVE",
  is_singular: false,
  assigned_by_user_id: 1,
  assignment_reason: "Fall allocation",
  created_at: "2026-08-01T00:00:00Z",
  updated_at: "2026-08-01T00:00:00Z",
};

describe("RolesPage", () => {
  beforeEach(() => {
    const idle = { mutate: vi.fn(), isPending: false };
    hooks.useRoles.mockReturnValue({
      data: [sampleRole],
      isLoading: false,
      isError: false,
    });
    hooks.useAssignRole.mockReturnValue(idle);
    hooks.useExtendRole.mockReturnValue(idle);
    hooks.useRevokeRole.mockReturnValue(idle);
    hooks.useReassignRole.mockReturnValue(idle);
  });

  it("renders role assignment controls", () => {
    render(
      <MantineProvider>
        <RolesPage />
      </MantineProvider>
    );

    expect(screen.getByText("Role Assignments")).toBeInTheDocument();
    expect(screen.getByText("Course Instructor")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /assign role/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Extend" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Revoke" })).toBeInTheDocument();
  });
});
