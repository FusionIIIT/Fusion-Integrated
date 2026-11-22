/** Data-access hooks for the superadmin module. */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  ArchivedUser,
  AuditLog,
  DashboardSummary,
  HistoricalArchive,
  Page,
  PolicyParameter,
  PurgeRequest,
} from "./types";

const KEY = "superadmin";
const BASE = "/superadmin";

export const keys = {
  dashboard: () => [KEY, "dashboard"] as const,
  archivedUsers: (f?: unknown) => [KEY, "archived-users", f] as const,
  historicalArchives: (f?: unknown) => [KEY, "historical-archives", f] as const,
  purgeRequests: (f?: unknown) => [KEY, "purge-requests", f] as const,
  policyParams: () => [KEY, "policy-params"] as const,
  auditLogs: (f?: unknown) => [KEY, "audit-logs", f] as const,
};

export function useDashboard() {
  return useQuery({
    queryKey: keys.dashboard(),
    queryFn: async () =>
      (await http.get<DashboardSummary>(`${BASE}/dashboard/`)).data,
  });
}

export function useArchivedUsers(filters?: Record<string, unknown>) {
  return useQuery({
    queryKey: keys.archivedUsers(filters),
    queryFn: async () =>
      (await http.get<Page<ArchivedUser>>(`${BASE}/archival/users/`, { params: filters })).data,
  });
}

export function useHistoricalArchives(filters?: Record<string, unknown>) {
  return useQuery({
    queryKey: keys.historicalArchives(filters),
    queryFn: async () =>
      (await http.get<Page<HistoricalArchive>>(`${BASE}/archival/datasets/`, { params: filters })).data,
  });
}

export function useRestoreUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: { user_id: number; restoration_reason: string }) =>
      (await http.post<ArchivedUser>(
        `${BASE}/archival/users/${data.user_id}/restore/`,
        { restoration_reason: data.restoration_reason },
      )).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: [KEY, "archived-users"] }),
  });
}

export function usePurgeRequests(filters?: Record<string, unknown>) {
  return useQuery({
    queryKey: keys.purgeRequests(filters),
    queryFn: async () =>
      (await http.get<Page<PurgeRequest>>(`${BASE}/purge/requests/`, { params: filters })).data,
  });
}

export function useCreatePurgeRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: { archive_id: number; request_reason: string }) =>
      (await http.post<PurgeRequest>(`${BASE}/purge/requests/`, data)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: [KEY, "purge-requests"] }),
  });
}

export function useDecidePurgeRequest() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: { id: number; approve: boolean; comments?: string }) =>
      (await http.post<PurgeRequest>(`${BASE}/purge/requests/${data.id}/decision/`, {
        approve: data.approve,
        comments: data.comments ?? "",
      })).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: [KEY, "purge-requests"] }),
  });
}

export function useExecutePurge() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<PurgeRequest>(`${BASE}/purge/requests/${id}/execute/`, {})).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: [KEY, "purge-requests"] });
      qc.invalidateQueries({ queryKey: [KEY, "historical-archives"] });
    },
  });
}

export function usePolicyParams() {
  return useQuery({
    queryKey: keys.policyParams(),
    queryFn: async () =>
      (await http.get<Page<PolicyParameter>>(`${BASE}/policy/parameters/`)).data,
  });
}

export function useSupersedePolicyParam() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: { key: string; value: string; description?: string }) =>
      (await http.post<PolicyParameter>(`${BASE}/policy/parameters/`, data)).data,
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.policyParams() }),
  });
}

export function useAuditLogs(filters?: Record<string, unknown>) {
  return useQuery({
    queryKey: keys.auditLogs(filters),
    queryFn: async () =>
      (await http.get<Page<AuditLog>>(`${BASE}/audit/logs/`, { params: filters })).data,
  });
}
