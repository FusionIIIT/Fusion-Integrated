import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { describe, expect, it, vi } from "vitest";

import { http } from "../../../lib/http";
import {
  useDashboardMetrics,
  useUsers,
  useCreateUser,
  useAssignRole,
  useArchiveUser,
  useAuditLogs,
} from "./hooks";

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("System Admin Hooks", () => {
  it("fetches dashboard metrics", async () => {
    const mockMetrics = {
      users: { total: 10, active: 8, deactivated: 1, archived: 1, by_type: [] },
      roles: { total_defined: 9, active_assignments: 5, vacant_singular_count: 0, vacant_singular_roles: [], expiring_soon_count: 0 },
      archival: { reversible_users: 1, permanent_users: 0, historical_batches: 2, pending_purge_requests: 0 },
      security: { active_sessions: 1, unresolved_alerts: 0, recent_failures_24h: 0, recent_actions: [] },
    };
    vi.spyOn(http, "get").mockResolvedValue({ data: mockMetrics });

    const { result } = renderHook(() => useDashboardMetrics(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.get).toHaveBeenCalledWith("/systemadmin/dashboard/");
    expect(result.current.data?.users.total).toBe(10);
  });

  it("fetches users list with filters", async () => {
    const mockUsers = {
      count: 1,
      results: [{ id: 1, institute_id: "24BCS142", full_name: "Srikanth Harsha", user_type: "student", status: "active" }],
    };
    vi.spyOn(http, "get").mockResolvedValue({ data: mockUsers });

    const { result } = renderHook(() => useUsers({ user_type: "student" }), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.get).toHaveBeenCalledWith("/systemadmin/users/", { params: { user_type: "student" } });
    expect(result.current.data?.results[0]?.institute_id).toBe("24BCS142");
  });

  it("executes create user mutation", async () => {
    const newUser = { id: 2, institute_id: "FAC001", full_name: "Dr. Faculty", user_type: "faculty", status: "active" };
    vi.spyOn(http, "post").mockResolvedValue({ data: newUser });

    const { result } = renderHook(() => useCreateUser(), { wrapper });
    result.current.mutate({
      institute_id: "FAC001",
      full_name: "Dr. Faculty",
      user_type: "faculty",
      institute_email: "fac001@iiitdmj.ac.in",
      department: "CSE",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.post).toHaveBeenCalledWith("/systemadmin/users/create/", expect.objectContaining({
      institute_id: "FAC001",
    }));
  });

  it("executes assign role mutation", async () => {
    const newAssignment = { id: 1, role_code: "HOD_CSE", user_id: 2, status: "active" };
    vi.spyOn(http, "post").mockResolvedValue({ data: newAssignment });

    const { result } = renderHook(() => useAssignRole(), { wrapper });
    result.current.mutate({
      role_code: "HOD_CSE",
      user_id: 2,
      start_date: "2026-11-01",
      scope: "CSE",
      reason: "Departmental appointment",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.post).toHaveBeenCalledWith("/systemadmin/assignments/create/", expect.objectContaining({
      role_code: "HOD_CSE",
    }));
  });

  it("executes user archival mutation", async () => {
    const mockArchived = { id: 1, user: 2, status: "reversible" };
    vi.spyOn(http, "post").mockResolvedValue({ data: mockArchived });

    const { result } = renderHook(() => useArchiveUser(), { wrapper });
    result.current.mutate({
      user_id: 2,
      reason: "Graduated student archival",
      retention_option: "standard_institutional",
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.post).toHaveBeenCalledWith("/systemadmin/archival/users/create/", expect.objectContaining({
      user_id: 2,
    }));
  });

  it("fetches audit logs with action filters", async () => {
    const mockLogs = {
      count: 1,
      results: [{ id: 1, action: "role_assign", actor_username: "admin", result: "SUCCESS" }],
    };
    vi.spyOn(http, "get").mockResolvedValue({ data: mockLogs });

    const { result } = renderHook(() => useAuditLogs({ action: "role_assign" }), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(http.get).toHaveBeenCalledWith("/systemadmin/audit/", { params: { action: "role_assign" } });
    expect(result.current.data?.results[0]?.action).toBe("role_assign");
  });
});
