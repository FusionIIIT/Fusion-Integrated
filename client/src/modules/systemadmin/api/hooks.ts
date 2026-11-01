/** React Query hooks for System Admin Module data access. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "../../../lib/http";
import type {
  BasicUser,
  BasicUserDetail,
  RoleDefinitionItem,
  RoleAssignmentItem,
  ArchivedUserItem,
  ArchivedHistoricalDataItem,
  PermanentPurgeRequestItem,
  AuditLogItem,
  SessionLogItem,
  SecurityAlertItem,
  AdminNotificationItem,
  ConfigItem,
  DashboardMetrics,
  AuditReportData,
  PageResponse,
} from "./types";

const KEY = "systemadmin";

export const keys = {
  dashboard: () => [KEY, "dashboard"] as const,
  users: (f?: unknown) => [KEY, "users", f] as const,
  user: (id: number) => [KEY, "user", id] as const,
  roles: () => [KEY, "roles"] as const,
  role: (id: number) => [KEY, "role", id] as const,
  assignments: (f?: unknown) => [KEY, "assignments", f] as const,
  archivedUsers: (f?: unknown) => [KEY, "archived-users", f] as const,
  historicalData: (f?: unknown) => [KEY, "historical-data", f] as const,
  purgeRequests: (f?: unknown) => [KEY, "purge-requests", f] as const,
  auditLogs: (f?: unknown) => [KEY, "audit-logs", f] as const,
  auditReport: (f?: unknown) => [KEY, "audit-report", f] as const,
  sessions: () => [KEY, "sessions"] as const,
  alerts: () => [KEY, "alerts"] as const,
  notifications: () => [KEY, "notifications"] as const,
  configs: () => [KEY, "configs"] as const,
};

function invalidate(qc: ReturnType<typeof useQueryClient>, ...subkeys: string[]) {
  qc.invalidateQueries({ queryKey: [KEY, ...subkeys] });
  qc.invalidateQueries({ queryKey: [KEY, "dashboard"] });
}

// -------------------------------------------------------------------------
// Dashboard
// -------------------------------------------------------------------------

export function useDashboardMetrics() {
  return useQuery({
    queryKey: keys.dashboard(),
    queryFn: async () => (await http.get<DashboardMetrics>("/systemadmin/dashboard/")).data,
    refetchInterval: 30_000,
  });
}

// -------------------------------------------------------------------------
// Users
// -------------------------------------------------------------------------

export function useUsers(filters?: { search?: string; user_type?: string; status?: string; department?: string }) {
  return useQuery({
    queryKey: keys.users(filters),
    queryFn: async () =>
      (await http.get<PageResponse<BasicUser>>("/systemadmin/users/", { params: filters })).data,
  });
}

export function useUser(userId: number | undefined) {
  return useQuery({
    queryKey: keys.user(userId!),
    queryFn: async () => (await http.get<BasicUserDetail>(`/systemadmin/users/${userId}/`)).data,
    enabled: Boolean(userId),
  });
}

export function useCreateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      (await http.post<BasicUser>("/systemadmin/users/create/", payload)).data,
    onSuccess: () => invalidate(qc, "users"),
  });
}

export function useUpdateUser(userId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Record<string, unknown>) =>
      (await http.patch<BasicUser>(`/systemadmin/users/${userId}/`, payload)).data,
    onSuccess: () => invalidate(qc, "users", "user"),
  });
}

export function useChangeUserStatus(userId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { action: "deactivate" | "reactivate"; reason: string }) =>
      (await http.post<BasicUser>(`/systemadmin/users/${userId}/status/`, payload)).data,
    onSuccess: () => invalidate(qc, "users", "user"),
  });
}

export function useBulkCreateUsers() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { users: Record<string, unknown>[] }) =>
      (await http.post<{ success_count: number; failure_count: number }>("/systemadmin/users/bulk-create/", payload)).data,
    onSuccess: () => invalidate(qc, "users"),
  });
}

export function useBulkUserStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { user_ids: number[]; action: "deactivate" | "reactivate"; reason: string }) =>
      (await http.post<{ success_count: number; failure_count: number }>("/systemadmin/users/bulk-status/", payload)).data,
    onSuccess: () => invalidate(qc, "users"),
  });
}

// -------------------------------------------------------------------------
// Roles & Assignments
// -------------------------------------------------------------------------

export function useRoles() {
  return useQuery({
    queryKey: keys.roles(),
    queryFn: async () =>
      (await http.get<PageResponse<RoleDefinitionItem>>("/systemadmin/roles/")).data,
  });
}

export function useRole(roleId: number | undefined) {
  return useQuery({
    queryKey: keys.role(roleId!),
    queryFn: async () => (await http.get<RoleDefinitionItem>(`/systemadmin/roles/${roleId}/`)).data,
    enabled: Boolean(roleId),
  });
}

export function useRoleAssignments(filters?: { role_id?: number; user_id?: number; status?: string }) {
  return useQuery({
    queryKey: keys.assignments(filters),
    queryFn: async () =>
      (await http.get<PageResponse<RoleAssignmentItem>>("/systemadmin/assignments/", { params: filters })).data,
  });
}

export function useAssignRole() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      role_code: string;
      user_id: number;
      start_date: string;
      end_date?: string | null;
      scope?: string;
      reason?: string;
    }) => (await http.post<RoleAssignmentItem>("/systemadmin/assignments/create/", payload)).data,
    onSuccess: () => {
      invalidate(qc, "assignments");
      invalidate(qc, "roles");
    },
  });
}

export function useReassignRole(assignmentId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      new_user_id: number;
      effective_date: string;
      reason: string;
      pending_task_disposition?: "transfer" | "close";
    }) => (await http.post<RoleAssignmentItem>(`/systemadmin/assignments/${assignmentId}/reassign/`, payload)).data,
    onSuccess: () => {
      invalidate(qc, "assignments");
      invalidate(qc, "roles");
    },
  });
}

export function useRevokeRole(assignmentId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      reason: string;
      is_emergency?: boolean;
      effective_date?: string | null;
      pending_task_disposition?: "transfer" | "close";
    }) => (await http.post<RoleAssignmentItem>(`/systemadmin/assignments/${assignmentId}/revoke/`, payload)).data,
    onSuccess: () => {
      invalidate(qc, "assignments");
      invalidate(qc, "roles");
    },
  });
}

export function useExtendRole(assignmentId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      new_end_date: string;
      extension_approval_ref: string;
      reason: string;
    }) => (await http.post<RoleAssignmentItem>(`/systemadmin/assignments/${assignmentId}/extend/`, payload)).data,
    onSuccess: () => {
      invalidate(qc, "assignments");
    },
  });
}

// -------------------------------------------------------------------------
// Archival & Purge
// -------------------------------------------------------------------------

export function useArchivedUsers(filters?: { status?: string; search?: string }) {
  return useQuery({
    queryKey: keys.archivedUsers(filters),
    queryFn: async () =>
      (await http.get<PageResponse<ArchivedUserItem>>("/systemadmin/archival/users/", { params: filters })).data,
  });
}

export function useArchiveUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { user_id: number; reason: string; retention_option?: string }) =>
      (await http.post<ArchivedUserItem>("/systemadmin/archival/users/create/", payload)).data,
    onSuccess: () => {
      invalidate(qc, "archived-users");
      invalidate(qc, "users");
    },
  });
}

export function useRestoreArchivedUser(userId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { restoration_authorization_ref: string }) =>
      (await http.post<BasicUser>(`/systemadmin/archival/users/${userId}/restore/`, payload)).data,
    onSuccess: () => {
      invalidate(qc, "archived-users");
      invalidate(qc, "users");
    },
  });
}

export function useArchivedHistoricalData(filters?: { category?: string; status?: string }) {
  return useQuery({
    queryKey: keys.historicalData(filters),
    queryFn: async () =>
      (await http.get<PageResponse<ArchivedHistoricalDataItem>>("/systemadmin/archival/historical/", { params: filters })).data,
  });
}

export function useArchiveHistoricalData() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      category: string;
      date_range_start: string;
      date_range_end: string;
      record_count: number;
      storage_size_kb: number;
      backup_reference: string;
      retention_years?: number;
    }) => (await http.post<ArchivedHistoricalDataItem>("/systemadmin/archival/historical/create/", payload)).data,
    onSuccess: () => invalidate(qc, "historical-data"),
  });
}

export function useRestoreHistoricalData(dataId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { approval_ref: string }) =>
      (await http.post<ArchivedHistoricalDataItem>(`/systemadmin/archival/historical/${dataId}/restore/`, payload)).data,
    onSuccess: () => invalidate(qc, "historical-data"),
  });
}

export function usePurgeRequests(filters?: { status?: string; target_type?: string }) {
  return useQuery({
    queryKey: keys.purgeRequests(filters),
    queryFn: async () =>
      (await http.get<PageResponse<PermanentPurgeRequestItem>>("/systemadmin/purge-requests/", { params: filters })).data,
  });
}

export function useCreatePurgeRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: {
      target_type: "historical_data" | "archived_user";
      target_id: number;
      reason: string;
      regulatory_authorization_ref: string;
    }) => (await http.post<PermanentPurgeRequestItem>("/systemadmin/purge-requests/create/", payload)).data,
    onSuccess: () => invalidate(qc, "purge-requests"),
  });
}

export function useAuthorizePurgeRequest(requestId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { decision: "approve" | "reject"; comments: string }) =>
      (await http.post<PermanentPurgeRequestItem>(`/systemadmin/purge-requests/${requestId}/authorize/`, payload)).data,
    onSuccess: () => {
      invalidate(qc, "purge-requests");
      invalidate(qc, "historical-data");
      invalidate(qc, "archived-users");
    },
  });
}

// -------------------------------------------------------------------------
// Audit Logs, Reports & Security
// -------------------------------------------------------------------------

export function useAuditLogs(filters?: {
  actor_username?: string;
  action?: string;
  result?: string;
  target_user?: string;
  start_date?: string;
  end_date?: string;
  search?: string;
}) {
  return useQuery({
    queryKey: keys.auditLogs(filters),
    queryFn: async () =>
      (await http.get<PageResponse<AuditLogItem>>("/systemadmin/audit/", { params: filters })).data,
  });
}

export function useAuditReport(filters?: { start_date?: string; end_date?: string }) {
  return useQuery({
    queryKey: keys.auditReport(filters),
    queryFn: async () =>
      (await http.get<AuditReportData>("/systemadmin/audit/reports/", { params: filters })).data,
  });
}

export function useSessions() {
  return useQuery({
    queryKey: keys.sessions(),
    queryFn: async () => (await http.get<PageResponse<SessionLogItem>>("/systemadmin/audit/sessions/")).data,
  });
}

export function useSecurityAlerts() {
  return useQuery({
    queryKey: keys.alerts(),
    queryFn: async () => (await http.get<PageResponse<SecurityAlertItem>>("/systemadmin/audit/alerts/")).data,
  });
}

export function useAdminNotifications() {
  return useQuery({
    queryKey: keys.notifications(),
    queryFn: async () => (await http.get<PageResponse<AdminNotificationItem>>("/systemadmin/notifications/")).data,
  });
}

// -------------------------------------------------------------------------
// Configuration
// -------------------------------------------------------------------------

export function useConfigurations() {
  return useQuery({
    queryKey: keys.configs(),
    queryFn: async () => (await http.get<PageResponse<ConfigItem>>("/systemadmin/config/")).data,
  });
}

export function useUpdateConfiguration(key: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { value: unknown; confirmation_token?: string }) =>
      (await http.patch<ConfigItem>(`/systemadmin/config/${key}/`, payload)).data,
    onSuccess: () => invalidate(qc, "configs"),
  });
}
