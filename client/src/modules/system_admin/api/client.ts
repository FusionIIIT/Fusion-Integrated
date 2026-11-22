/** API client functions for System Admin endpoints. */
import { http } from "../../../lib/http";
import type {
  ArchivedUserRecord,
  DashboardMetrics,
  FailedLoginLog,
  HistoricalDatasetArchive,
  PermanentPurgeRequest,
  RoleAssignment,
  RoleDirectoryEntry,
  SystemAuditLog,
  UserAccount,
} from "./types";

export const adminApi = {
  // Dashboard
  getDashboard: async () => {
    const res = await http.get<DashboardMetrics>("/system_admin/dashboard/");
    return res.data;
  },

  // Users
  getUsers: async (params?: { q?: string; user_type?: string; status?: string; limit?: number; offset?: number }) => {
    const res = await http.get<{ results: UserAccount[]; total: number }>("/system_admin/users/", { params });
    return res.data;
  },

  createUser: async (payload: Partial<UserAccount>) => {
    const res = await http.post<UserAccount>("/system_admin/users/create/", payload);
    return res.data;
  },

  updateUser: async (userId: number, payload: Partial<UserAccount>) => {
    const res = await http.patch<UserAccount>(`/system_admin/users/${userId}/`, payload);
    return res.data;
  },

  updateUserStatus: async (userId: number, action: "deactivate" | "reactivate", reason: string) => {
    const res = await http.post<UserAccount>(`/system_admin/users/${userId}/status/`, { action, reason });
    return res.data;
  },

  bulkCreateUsers: async (users: Array<Partial<UserAccount>>) => {
    const res = await http.post<{ created_count: number; error_count: number; errors: unknown[] }>(
      "/system_admin/users/bulk-create/",
      { users },
    );
    return res.data;
  },

  // Roles
  getRoles: async (params?: { user_id?: number; role_code?: string; status?: string }) => {
    const res = await http.get<RoleAssignment[]>("/system_admin/roles/", { params });
    return res.data;
  },

  getRoleDirectory: async () => {
    const res = await http.get<RoleDirectoryEntry[]>("/system_admin/roles/?mode=directory");
    return res.data;
  },

  assignRole: async (payload: {
    role_code: string;
    user_id: number;
    start_date: string;
    end_date?: string | null;
    scope?: string;
    reason?: string;
    is_singular?: boolean;
  }) => {
    const res = await http.post<RoleAssignment>("/system_admin/roles/assign/", payload);
    return res.data;
  },

  reassignRole: async (roleId: number, payload: { new_user_id: number; effective_date: string; reason: string }) => {
    const res = await http.post<RoleAssignment>(`/system_admin/roles/${roleId}/reassign/`, payload);
    return res.data;
  },

  revokeRole: async (roleId: number, reason: string, isEmergency = false) => {
    const res = await http.post<RoleAssignment>(`/system_admin/roles/${roleId}/revoke/`, {
      reason,
      is_emergency: isEmergency,
    });
    return res.data;
  },

  extendRole: async (roleId: number, newEndDate: string, reason: string) => {
    const res = await http.post<RoleAssignment>(`/system_admin/roles/${roleId}/extend/`, {
      new_end_date: newEndDate,
      reason,
    });
    return res.data;
  },

  // Archives
  getArchivedUsers: async (params?: { q?: string; user_type?: string; limit?: number; offset?: number }) => {
    const res = await http.get<{ results: ArchivedUserRecord[]; total: number }>("/system_admin/archives/", {
      params,
    });
    return res.data;
  },

  archiveUser: async (userId: number, reason: string, retentionOption = "standard_7yr", reversibleDays = 90) => {
    const res = await http.post<ArchivedUserRecord>("/system_admin/archives/user/", {
      user_id: userId,
      reason,
      retention_option: retentionOption,
      reversible_days: reversibleDays,
    });
    return res.data;
  },

  restoreUser: async (userId: number, reason: string) => {
    const res = await http.post<UserAccount>(`/system_admin/archives/user/${userId}/restore/`, { reason });
    return res.data;
  },

  getDatasets: async () => {
    const res = await http.get<HistoricalDatasetArchive[]>("/system_admin/archives/?mode=datasets");
    return res.data;
  },

  archiveDataset: async (payload: {
    category: string;
    description: string;
    date_range_start: string;
    date_range_end: string;
    backup_reference: string;
    record_count?: number;
  }) => {
    const res = await http.post<HistoricalDatasetArchive>("/system_admin/archives/dataset/", payload);
    return res.data;
  },

  getPurgeRequests: async () => {
    const res = await http.get<PermanentPurgeRequest[]>("/system_admin/archives/?mode=purge_requests");
    return res.data;
  },

  requestPurge: async (datasetIdentifier: string, retentionYears: number, reason: string) => {
    const res = await http.post<PermanentPurgeRequest>("/system_admin/archives/purge-request/", {
      dataset_identifier: datasetIdentifier,
      retention_years: retentionYears,
      reason,
    });
    return res.data;
  },

  authorizePurge: async (purgeId: number, approve: boolean, remarks = "") => {
    const res = await http.post<PermanentPurgeRequest>(
      `/system_admin/archives/purge-request/${purgeId}/authorize/`,
      { approve, remarks },
    );
    return res.data;
  },

  // Audit
  getAuditLogs: async (params?: { action?: string; target_id?: string; limit?: number; offset?: number }) => {
    const res = await http.get<{ results: SystemAuditLog[]; total: number }>("/system_admin/audit/", { params });
    return res.data;
  },

  getFailedLogins: async () => {
    const res = await http.get<FailedLoginLog[]>("/system_admin/audit/failed-logins/");
    return res.data;
  },

  // Config
  getParameters: async () => {
    const res = await http.get<{ parameters: Record<string, string> }>("/system_admin/config/");
    return res.data.parameters;
  },

  updateParameters: async (parameters: Record<string, string>) => {
    const res = await http.patch<{ parameters: Record<string, string> }>("/system_admin/config/", { parameters });
    return res.data.parameters;
  },
};
