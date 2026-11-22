/** TanStack Query hooks for Super Admin endpoints. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  AuditLogEntry,
  DashboardMetrics,
  HistoricalArchive,
  PurgeRequest,
  RoleAssignment,
  SystemParameter,
  UserAccount,
} from "./types";

export function useUsers(filters?: { search?: string; user_type?: string; status?: string }) {
  return useQuery({
    queryKey: ["superadmin", "users", filters],
    queryFn: async () => {
      const { data } = await http.get<UserAccount[]>("/superadmin/users/", { params: filters });
      return data;
    },
  });
}

export function useUserDetail(userId: number) {
  return useQuery({
    queryKey: ["superadmin", "users", userId],
    queryFn: async () => {
      const { data } = await http.get<UserAccount>(`/superadmin/users/${userId}/`);
      return data;
    },
    enabled: Boolean(userId),
  });
}

export function useCreateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      user_id: number;
      institute_id: string;
      email: string;
      user_type: string;
      department?: string;
      program?: string;
      batch?: string;
    }) => {
      const { data } = await http.post<UserAccount>("/superadmin/users/", payload);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["superadmin", "users"] });
      qc.invalidateQueries({ queryKey: ["superadmin", "dashboard"] });
    },
  });
}

export function useDeactivateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ userId, reason }: { userId: number; reason: string }) => {
      const { data } = await http.post<UserAccount>(`/superadmin/users/${userId}/deactivate/`, { reason });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["superadmin", "users"] });
      qc.invalidateQueries({ queryKey: ["superadmin", "dashboard"] });
    },
  });
}

export function useReactivateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ userId, reason }: { userId: number; reason: string }) => {
      const { data } = await http.post<UserAccount>(`/superadmin/users/${userId}/reactivate/`, { reason });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["superadmin", "users"] });
      qc.invalidateQueries({ queryKey: ["superadmin", "dashboard"] });
    },
  });
}

export function useArchiveUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ userId, reason }: { userId: number; reason: string }) => {
      const { data } = await http.post<UserAccount>(`/superadmin/users/${userId}/archive/`, { reason });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["superadmin", "users"] });
      qc.invalidateQueries({ queryKey: ["superadmin", "dashboard"] });
    },
  });
}

export function useRestoreUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ userId, reason }: { userId: number; reason: string }) => {
      const { data } = await http.post<UserAccount>(`/superadmin/users/${userId}/restore/`, { reason });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["superadmin", "users"] });
      qc.invalidateQueries({ queryKey: ["superadmin", "dashboard"] });
    },
  });
}

export function useRoles(filters?: { user_id?: number; role_name?: string; status?: string }) {
  return useQuery({
    queryKey: ["superadmin", "roles", filters],
    queryFn: async () => {
      const { data } = await http.get<RoleAssignment[]>("/superadmin/roles/", { params: filters });
      return data;
    },
  });
}

export function useAssignRole() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      user_id: number;
      role_name: string;
      valid_from: string;
      valid_to?: string | null;
      scope_type?: string;
      scope_id?: string;
      is_singular?: boolean;
      reason?: string;
    }) => {
      const { data } = await http.post<RoleAssignment>("/superadmin/roles/", payload);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["superadmin", "roles"] });
    },
  });
}

export function useExtendRole() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ assignmentId, new_valid_to, reason }: { assignmentId: number; new_valid_to: string; reason: string }) => {
      const { data } = await http.post<RoleAssignment>(`/superadmin/roles/${assignmentId}/extend/`, { new_valid_to, reason });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["superadmin", "roles"] });
    },
  });
}

export function useRevokeRole() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ assignmentId, reason }: { assignmentId: number; reason: string }) => {
      const { data } = await http.post<RoleAssignment>(`/superadmin/roles/${assignmentId}/revoke/`, { reason });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["superadmin", "roles"] });
    },
  });
}

export function useArchives(filters?: { entity_type?: string; status?: string }) {
  return useQuery({
    queryKey: ["superadmin", "archives", filters],
    queryFn: async () => {
      const { data } = await http.get<HistoricalArchive[]>("/superadmin/archive/", { params: filters });
      return data;
    },
  });
}

export function usePurgeRequests(statusFilter?: string) {
  return useQuery({
    queryKey: ["superadmin", "purge_requests", statusFilter],
    queryFn: async () => {
      const { data } = await http.get<PurgeRequest[]>("/superadmin/purge/requests/", {
        params: statusFilter ? { status: statusFilter } : undefined,
      });
      return data;
    },
  });
}

export function useRequestPurge() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ archive_id, reason }: { archive_id: number; reason: string }) => {
      const { data } = await http.post<PurgeRequest>("/superadmin/purge/requests/", { archive_id, reason });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["superadmin", "purge_requests"] });
    },
  });
}

export function useAuthorizePurge() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ requestId, action, reason }: { requestId: number; action: "APPROVE" | "REJECT"; reason?: string }) => {
      const { data } = await http.post<PurgeRequest>(`/superadmin/purge/requests/${requestId}/authorize/`, { action, reason });
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["superadmin", "purge_requests"] });
      qc.invalidateQueries({ queryKey: ["superadmin", "archives"] });
    },
  });
}

export function useAuditLogs(filters?: { event_type?: string; target_entity?: string }) {
  return useQuery({
    queryKey: ["superadmin", "audit_logs", filters],
    queryFn: async () => {
      const { data } = await http.get<AuditLogEntry[]>("/superadmin/audit/", { params: filters });
      return data;
    },
  });
}

export function useSystemParameters() {
  return useQuery({
    queryKey: ["superadmin", "system_parameters"],
    queryFn: async () => {
      const { data } = await http.get<SystemParameter[]>("/superadmin/config/");
      return data;
    },
  });
}

export function useUpdateSystemParameter() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { parameter_key: string; parameter_value: Record<string, unknown>; effective_from?: string }) => {
      const { data } = await http.post<SystemParameter>("/superadmin/config/", payload);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["superadmin", "system_parameters"] });
    },
  });
}

export function useDashboardMetrics() {
  return useQuery({
    queryKey: ["superadmin", "dashboard"],
    queryFn: async () => {
      const { data } = await http.get<DashboardMetrics>("/superadmin/dashboard/");
      return data;
    },
  });
}
