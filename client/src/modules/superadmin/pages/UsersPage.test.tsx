import { MantineProvider } from "@mantine/core";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { UserAccount } from "../api/types";
import UsersPage from "./UsersPage";

const hooks = vi.hoisted(() => ({
  useUsers: vi.fn(),
  useCreateUser: vi.fn(),
  useDeactivateUser: vi.fn(),
  useReactivateUser: vi.fn(),
  useArchiveUser: vi.fn(),
  useRestoreUser: vi.fn(),
}));
vi.mock("../api/hooks", () => hooks);

const sampleUser: UserAccount = {
  id: 1,
  user_id: 101,
  institute_id: "24BCS101",
  email: "u101@iiitdmj.ac.in",
  user_type: "STUDENT",
  activation_status: "ACTIVE",
  deactivation_date: null,
  archival_date: null,
  reversibility_expires_at: null,
  department: "CSE",
  program: "B.Tech",
  batch: "2024",
  created_at: "2026-08-01T00:00:00Z",
  updated_at: "2026-08-01T00:00:00Z",
};

describe("UsersPage", () => {
  beforeEach(() => {
    const idle = { mutate: vi.fn(), isPending: false };
    hooks.useUsers.mockReturnValue({
      data: [sampleUser],
      isLoading: false,
      isError: false,
    });
    hooks.useCreateUser.mockReturnValue(idle);
    hooks.useDeactivateUser.mockReturnValue(idle);
    hooks.useReactivateUser.mockReturnValue(idle);
    hooks.useArchiveUser.mockReturnValue(idle);
    hooks.useRestoreUser.mockReturnValue(idle);
  });

  it("renders user table and action buttons", () => {
    render(
      <MantineProvider>
        <UsersPage />
      </MantineProvider>
    );

    expect(screen.getByText("User Accounts")).toBeInTheDocument();
    expect(screen.getByText("24BCS101")).toBeInTheDocument();
    expect(screen.getByText("u101@iiitdmj.ac.in")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /create account/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Deactivate" })).toBeInTheDocument();
  });
});
