import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  ArchivalRequest,
  AuditEvent,
  BackupRecord,
  BackupSchedule,
  DataClassification,
  DepartmentReport,
  RestorationRequest,
  SecurityPolicy,
  StorageExtensionRequest,
} from "./types";

export interface PaginatedResponse<T> {
  results: T[];
  count?: number;
}

export interface CreateArchivalRequestPayload {
  department?: string;
  file_name: string;
  file_type: string;
  file_size_bytes: number;
  reason: string;
  file_storage_path: string;
  initial_classification?: DataClassification;
}

export interface CreateStorageExtensionPayload {
  department?: string;
  requested_extension_bytes: number;
  justification: string;
}

export interface CreateRestorationPayload {
  archival_request_id: number;
  target_destination: string;
}

const KEY = "badms";

export function useBackups() {
  return useQuery({
    queryKey: [KEY, "backups"],
    queryFn: async () => (await http.get<PaginatedResponse<BackupRecord>>("/badms/backups/")).data,
  });
}

export function useTriggerManualBackup() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (datasetName: string) =>
      (await http.post<BackupRecord>("/badms/backups/manual/", { dataset_name: datasetName })).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [KEY, "backups"] });
    },
  });
}

export function useBackupSchedules() {
  return useQuery({
    queryKey: [KEY, "schedules"],
    queryFn: async () => (await http.get<PaginatedResponse<BackupSchedule>>("/badms/schedules/")).data,
  });
}

export function useArchivalRequests() {
  return useQuery({
    queryKey: [KEY, "archival-requests"],
    queryFn: async () => (await http.get<PaginatedResponse<ArchivalRequest>>("/badms/archival-requests/")).data,
  });
}

export function useCreateArchivalRequest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateArchivalRequestPayload) =>
      (await http.post<ArchivalRequest>("/badms/archival-requests/", payload)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [KEY, "archival-requests"] });
    },
  });
}

export function useStorageExtensions() {
  return useQuery({
    queryKey: [KEY, "storage-extensions"],
    queryFn: async () =>
      (await http.get<PaginatedResponse<StorageExtensionRequest>>("/badms/storage-extensions/")).data,
  });
}

export function useCreateStorageExtension() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateStorageExtensionPayload) =>
      (await http.post<StorageExtensionRequest>("/badms/storage-extensions/", payload)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [KEY, "storage-extensions"] });
    },
  });
}

export function useRestorations() {
  return useQuery({
    queryKey: [KEY, "restorations"],
    queryFn: async () => (await http.get<PaginatedResponse<RestorationRequest>>("/badms/restorations/")).data,
  });
}

export function useCreateRestoration() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateRestorationPayload) =>
      (await http.post<RestorationRequest>("/badms/restorations/", payload)).data,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [KEY, "restorations"] });
    },
  });
}

export function useAuditLogs() {
  return useQuery({
    queryKey: [KEY, "audit-logs"],
    queryFn: async () => (await http.get<PaginatedResponse<AuditEvent>>("/badms/audit-logs/")).data,
  });
}

export function useDepartmentReport(department: string) {
  return useQuery({
    queryKey: [KEY, "report", department],
    queryFn: async () =>
      (await http.get<DepartmentReport>(`/badms/reports/department/?department=${encodeURIComponent(department)}`)).data,
    enabled: Boolean(department),
  });
}

export function useSecurityPolicies() {
  return useQuery({
    queryKey: [KEY, "security-policies"],
    queryFn: async () => (await http.get<PaginatedResponse<SecurityPolicy>>("/badms/security-policies/")).data,
  });
}
