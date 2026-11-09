/** Data access hooks for modules.system_admin.
 *  Uses TanStack React Query for caching, polling, and cache invalidation.
 */
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  AdminUser,
  ArchivedUserRecord,
  AssignRolePayload,
  AuthorizePurgePayload,
  BulkStatusUpdatePayload,
  CreateUserPayload,
  DashboardMetrics,
  Page,
  PurgeRequest,
  ReassignRolePayload,
  RequestPurgePayload,
  RevokeRolePayload,
  RoleAssignment,
  RoleDefinition,
  AuditLog,
  SystemParameter,
  UpdateUserStatusPayload,
} from "./types";

const KEY = "system_admin";

export const keys = {
  all: [KEY] as const,
  dashboard: () => [KEY, "dashboard"] as const,
  users: (filters?: Record<string, unknown>) => [KEY, "users", filters] as const,
  user: (id: number) => [KEY, "user", id] as const,
  roles: () => [KEY, "roles"] as const,
  roleDefinitions: () => [KEY, "role-definitions"] as const,
  archival: () => [KEY, "archival"] as const,
  purgeRequests: () => [KEY, "purge-requests"] as const,
  auditLogs: (filters?: Record<string, unknown>) => [KEY, "audit-logs", filters] as const,
  securityAlerts: () => [KEY, "security-alerts"] as const,
  parameters: () => [KEY, "parameters"] as const,
};

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

// ------------------------------------------------------------------------------
// Dashboard
// ------------------------------------------------------------------------------
export function useDashboardMetrics() {
  return useQuery({
    queryKey: keys.dashboard(),
    queryFn: async () =>
      (await http.get<DashboardMetrics>("/system_admin/dashboard/metrics/")).data,
    staleTime: 15_000,
    refetchInterval: 60_000,
  });
}

// ------------------------------------------------------------------------------
// Users
// ------------------------------------------------------------------------------
export function useUsers(filters?: {
  search?: string;
  kind?: string;
  status?: string;
  department?: string;
  page?: number;
}) {
  return useQuery({
    queryKey: keys.users(filters),
    queryFn: async () =>
      (
        await http.get<Page<AdminUser> | AdminUser[]>("/system_admin/users/", {
          params: filters,
        })
      ).data,
    staleTime: 30_000,
  });
}

export function useUser(id?: number) {
  return useQuery({
    queryKey: keys.user(id!),
    queryFn: async () =>
      (await http.get<AdminUser>(`/system_admin/users/${id}/`)).data,
    enabled: id != null,
  });
}

export function useCreateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateUserPayload) =>
      (await http.post<AdminUser>("/system_admin/users/", payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useUpdateUserStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      payload,
    }: {
      id: number;
      payload: UpdateUserStatusPayload;
    }) =>
      (
        await http.post<AdminUser>(
          `/system_admin/users/${id}/status/`,
          payload,
        )
      ).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useBulkUploadUsers() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (formData: FormData) =>
      (
        await http.post<{
          total: number;
          processed: number;
          failed: number;
          error_details: unknown[];
        }>("/system_admin/users/bulk-create/", formData, {
          headers: { "Content-Type": "multipart/form-data" },
        })
      ).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useBulkUpdateStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: BulkStatusUpdatePayload) =>
      (
        await http.post<{
          total: number;
          succeeded: number;
          failed: number;
          errors: unknown[];
        }>("/system_admin/users/bulk-status/", payload)
      ).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// ------------------------------------------------------------------------------
// Roles
// ------------------------------------------------------------------------------
export function useRoles() {
  return useQuery({
    queryKey: keys.roles(),
    queryFn: async () => {
      const res = await http.get<
        Page<RoleAssignment> | { definitions: RoleDefinition[]; assignments: RoleAssignment[] } | RoleAssignment[]
      >("/system_admin/roles/");
      return res.data;
    },
    staleTime: 30_000,
  });
}

export function useAssignRole() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: AssignRolePayload) =>
      (await http.post<RoleAssignment>("/system_admin/roles/assign/", payload))
        .data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useReassignRole() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: ReassignRolePayload) =>
      (
        await http.post<RoleAssignment>(
          "/system_admin/roles/reassign/",
          payload,
        )
      ).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRevokeRole() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: RevokeRolePayload) =>
      (await http.post<RoleAssignment>("/system_admin/roles/revoke/", payload))
        .data,
    onSuccess: () => invalidateAll(qc),
  });
}

// ------------------------------------------------------------------------------
// Archival & Purge
// ------------------------------------------------------------------------------
export function useArchivedUsers() {
  return useQuery({
    queryKey: keys.archival(),
    queryFn: async () =>
      (
        await http.get<Page<ArchivedUserRecord> | ArchivedUserRecord[]>(
          "/system_admin/archival/",
        )
      ).data,
    staleTime: 30_000,
  });
}

export function useArchiveUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { user_id: number; reason: string }) =>
      (
        await http.post<ArchivedUserRecord>(
          "/system_admin/archival/archive-user/",
          payload,
        )
      ).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useRestoreUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { archive_id: number; reason: string }) =>
      (
        await http.post<{ detail: string }>(
          "/system_admin/archival/restore-user/",
          payload,
        )
      ).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function usePurgeRequests() {
  return useQuery({
    queryKey: keys.purgeRequests(),
    queryFn: async () =>
      (
        await http.get<Page<PurgeRequest> | PurgeRequest[]>(
          "/system_admin/purge/",
        )
      ).data,
    staleTime: 15_000,
  });
}

export function useRequestPurge() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: RequestPurgePayload) =>
      (
        await http.post<PurgeRequest>(
          "/system_admin/purge/request-purge/",
          payload,
        )
      ).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useAuthorizePurge() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      payload,
    }: {
      id: number;
      payload: AuthorizePurgePayload;
    }) =>
      (
        await http.post<PurgeRequest>(
          `/system_admin/purge/${id}/authorize/`,
          payload,
        )
      ).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// ------------------------------------------------------------------------------
// Audit & Security
// ------------------------------------------------------------------------------
export function useAuditLogs(filters?: {
  actor_username?: string;
  action?: string;
  result?: string;
  limit?: number;
}) {
  return useQuery({
    queryKey: keys.auditLogs(filters),
    queryFn: async () =>
      (
        await http.get<Page<AuditLog> | AuditLog[]>("/system_admin/audit/", {
          params: filters,
        })
      ).data,
    staleTime: 15_000,
  });
}

export function useSecurityAlerts() {
  return useQuery({
    queryKey: keys.securityAlerts(),
    queryFn: async () =>
      (await http.get<unknown[]>("/system_admin/audit/security-alerts/")).data,
    staleTime: 15_000,
  });
}

// ------------------------------------------------------------------------------
// System Parameters
// ------------------------------------------------------------------------------
export function useSystemParameters() {
  return useQuery({
    queryKey: keys.parameters(),
    queryFn: async () =>
      (
        await http.get<Record<string, string> | SystemParameter[]>(
          "/system_admin/config/parameters/",
        )
      ).data,
    staleTime: 60_000,
  });
}

export function useUpdateSystemParameter() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ key, value }: { key: string; value: string }) =>
      (
        await http.put<SystemParameter>(
          `/system_admin/config/parameters/${key}/`,
          { value },
        )
      ).data,
    onSuccess: () => invalidateAll(qc),
  });
}
