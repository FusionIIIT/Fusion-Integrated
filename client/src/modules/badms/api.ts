import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { http } from "../../lib/http";

export interface UserStorageQuota {
  id: number;
  user_id: number;
  department: string;
  allocated_bytes: number;
  used_bytes: number;
  remaining_bytes: number;
  created_at: string;
  updated_at: string;
}

export type ArchiveClassification = "routine" | "sensitive" | "critical" | "archival";

export type ArchiveStatus =
  | "draft"
  | "submitted"
  | "rejected"
  | "hod_approved"
  | "policy_applied"
  | "routed_to_security"
  | "encryption_configured"
  | "encrypted_archive_created";

export interface ArchivalRequest {
  id: number;
  user_id: number;
  department: string;
  file_name: string;
  document_date: string;
  owners: string[];
  file_type: string;
  file_size_bytes: number;
  attachment_path: string;
  reason: string;
  initial_classification: ArchiveClassification;
  authoritative_classification: ArchiveClassification | null;
  status: ArchiveStatus;
  checksum: string;
  encryption_algorithm: string;
  is_encrypted: boolean;
  hod_user_id: number | null;
  hod_comments: string;
  hod_decided_at: string | null;
  sysadmin_user_id: number | null;
  sysadmin_comments: string;
  sysadmin_classified_at: string | null;
  security_user_id: number | null;
  security_configured_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface BadmsNotification {
  id: number;
  user_id: number;
  recipient_role: string;
  subject: string;
  message: string;
  notification_type: string;
  related_object_id: string;
  is_read: boolean;
  created_at: string;
}

export interface SubmitArchivePayload {
  file_name: string;
  document_date: string;
  owners?: string[];
  file_type: string;
  file_size_bytes?: number;
  reason: string;
  initial_classification?: ArchiveClassification;
  attachment_path?: string;
  checksum?: string;
}

export interface HodReviewPayload {
  decision: "approve" | "reject";
  comments?: string;
}

export interface ClassifyPayload {
  classification: ArchiveClassification;
  comments?: string;
}

export interface ConfigureEncryptionPayload {
  algorithm?: string;
  key_id?: string;
}

export interface StorageExtensionRequest {
  id: number;
  user_id: number;
  department: string;
  current_allocated_bytes: number;
  requested_bytes: number;
  reason: string;
  status: "submitted" | "hod_approved" | "rejected";
  hod_user_id: number | null;
  hod_comments: string;
  decided_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface SubmitStorageExtensionPayload {
  requested_bytes: number;
  reason: string;
}

export interface StorageExtensionDecisionPayload {
  decision: "approve" | "reject";
  comments?: string;
}

export interface BackupExecution {
  id: number;
  backup_type: "manual" | "scheduled";
  scope: "local" | "global";
  target_dataset: string;
  status: "pending" | "in_progress" | "completed" | "failed";
  started_at: string;
  completed_at: string | null;
  size_bytes: number;
  checksum: string;
  repository_reachable: boolean;
  integrity_verified: boolean;
  error_message: string;
  consecutive_failure_count: number;
  initiated_by_user_id: number | null;
}

export interface BackupSchedule {
  id: number;
  name: string;
  schedule_type: "local" | "global";
  target_dataset: string;
  frequency: "hourly" | "daily" | "weekly" | "monthly";
  execution_time: string;
  classification_filter: string;
  is_active: boolean;
  repository_path: string;
  created_by_user_id: number | null;
  created_at: string;
}

export interface RestorationRequest {
  id: number;
  archive_id: number | null;
  backup_id: number | null;
  requester_user_id: number;
  target_type: string;
  target_name: string;
  reason: string;
  target_destination: string;
  is_sensitive: boolean;
  status: "pending_approval" | "approved" | "restoring" | "completed" | "rejected" | "failed";
  approved_by_user_id: number | null;
  approved_at: string | null;
  restored_at: string | null;
  integrity_verified: boolean;
  error_message: string;
  created_at: string;
}

export interface SpecialArchivalRecord {
  id: number;
  requester_name: string;
  requester_designation: string;
  dataset_title: string;
  classification: string;
  offline_media_type: string;
  media_serial_number: string;
  storage_vault_location: string;
  performed_by_user_id: number;
  notes: string;
  completed_at: string;
  checksum: string;
  created_at: string;
}

export interface BadmsAuditLog {
  id: number;
  actor_user_id: number;
  actor_role: string;
  action: string;
  target_type: string;
  target_id: string;
  outcome: string;
  details: Record<string, unknown>;
  ip_address: string;
  created_at: string;
}

export interface ComplianceSummary {
  archives: {
    total: number;
    compliant_count: number;
    compliance_rate_percent: number;
    by_classification: Record<string, number>;
    by_status: Record<string, number>;
  };
  backups: {
    total: number;
    successful: number;
    failed: number;
    consecutive_failures: number;
    last_backup_status: string;
    last_backup_at: string | null;
  };
  restorations: {
    total: number;
    completed: number;
    pending: number;
  };
  special_archives: {
    total: number;
  };
  storage: {
    total_allocated_bytes: number;
    total_used_bytes: number;
    total_remaining_bytes: number;
    utilization_percent: number;
  };
  audit_logs_count: number;
}

export interface SubmitRestorationPayload {
  archive_id?: number | null;
  backup_id?: number | null;
  reason: string;
  target_destination?: string;
}

export interface RestorationDecisionPayload {
  decision: "approve" | "reject";
  comments?: string;
}

export interface TriggerBackupPayload {
  scope?: "local" | "global";
  target_dataset?: string;
}

export interface SubmitSpecialArchivalPayload {
  requester_name: string;
  requester_designation: string;
  dataset_title: string;
  classification?: string;
  offline_media_type: string;
  media_serial_number: string;
  storage_vault_location: string;
  notes?: string;
}

export const badmsKeys = {
  all: ["badms"] as const,
  archives: (filters?: Record<string, string>) => ["badms", "archives", filters] as const,
  archive: (id: number) => ["badms", "archive", id] as const,
  quota: () => ["badms", "quota"] as const,
  notifications: () => ["badms", "notifications"] as const,
  storageExtensions: (filters?: Record<string, string>) =>
    ["badms", "storage-extensions", filters] as const,
  backups: () => ["badms", "backups"] as const,
  schedules: () => ["badms", "schedules"] as const,
  restorations: () => ["badms", "restorations"] as const,
  specialArchives: () => ["badms", "special-archives"] as const,
  auditLogs: (filters?: Record<string, string>) => ["badms", "audit-logs", filters] as const,
  complianceReport: () => ["badms", "reports", "summary"] as const,
};

export function useArchives(filters?: { status?: string; department?: string }) {
  return useQuery({
    queryKey: badmsKeys.archives(filters),
    queryFn: async () => {
      const { data } = await http.get<{ count: number; results: ArchivalRequest[] }>(
        "/badms/archives/",
        { params: filters },
      );
      return data;
    },
  });
}

export function useArchive(id: number) {
  return useQuery({
    queryKey: badmsKeys.archive(id),
    queryFn: async () => {
      const { data } = await http.get<ArchivalRequest>(`/badms/archives/${id}/`);
      return data;
    },
    enabled: Boolean(id),
  });
}

export function useUserQuota() {
  return useQuery({
    queryKey: badmsKeys.quota(),
    queryFn: async () => {
      const { data } = await http.get<UserStorageQuota>("/badms/quota/");
      return data;
    },
  });
}

export function useNotifications() {
  return useQuery({
    queryKey: badmsKeys.notifications(),
    queryFn: async () => {
      const { data } = await http.get<{ count: number; results: BadmsNotification[] }>(
        "/badms/notifications/",
      );
      return data;
    },
  });
}

export function useSubmitArchive() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: SubmitArchivePayload) => {
      const { data } = await http.post<ArchivalRequest>("/badms/archives/", payload);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: badmsKeys.all });
    },
  });
}

export function useHodReview() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: HodReviewPayload }) => {
      const { data } = await http.post<ArchivalRequest>(
        `/badms/archives/${id}/hod-decision/`,
        payload,
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: badmsKeys.all });
    },
  });
}

export function useClassifyArchive() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: ClassifyPayload }) => {
      const { data } = await http.post<ArchivalRequest>(
        `/badms/archives/${id}/classify/`,
        payload,
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: badmsKeys.all });
    },
  });
}

export function useConfigureEncryption() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      payload,
    }: {
      id: number;
      payload: ConfigureEncryptionPayload;
    }) => {
      const { data } = await http.post<ArchivalRequest>(
        `/badms/archives/${id}/configure-encryption/`,
        payload,
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: badmsKeys.all });
    },
  });
}

export function useStorageExtensions(filters?: { status?: string; department?: string }) {
  return useQuery({
    queryKey: badmsKeys.storageExtensions(filters as Record<string, string>),
    queryFn: async () => {
      const { data } = await http.get<{ count: number; results: StorageExtensionRequest[] }>(
        "/badms/storage-extensions/",
        { params: filters },
      );
      return data;
    },
  });
}

export function useSubmitStorageExtension() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: SubmitStorageExtensionPayload) => {
      const { data } = await http.post<StorageExtensionRequest>(
        "/badms/storage-extensions/",
        payload,
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: badmsKeys.all });
    },
  });
}

export function useStorageExtensionDecision() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      payload,
    }: {
      id: number;
      payload: StorageExtensionDecisionPayload;
    }) => {
      const { data } = await http.post<StorageExtensionRequest>(
        `/badms/storage-extensions/${id}/decision/`,
        payload,
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: badmsKeys.all });
    },
  });
}

// Backups & Schedules
export function useBackups() {
  return useQuery({
    queryKey: badmsKeys.backups(),
    queryFn: async () => {
      const { data } = await http.get<{ count: number; results: BackupExecution[] }>(
        "/badms/backups/",
      );
      return data;
    },
  });
}

export function useTriggerBackup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: TriggerBackupPayload) => {
      const { data } = await http.post<BackupExecution>("/badms/backups/", payload);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: badmsKeys.all });
    },
  });
}

export function useVerifyBackupIntegrity() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const { data } = await http.post<BackupExecution>(`/badms/backups/${id}/verify/`);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: badmsKeys.all });
    },
  });
}

export function useBackupSchedules() {
  return useQuery({
    queryKey: badmsKeys.schedules(),
    queryFn: async () => {
      const { data } = await http.get<{ count: number; results: BackupSchedule[] }>(
        "/badms/schedules/",
      );
      return data;
    },
  });
}

export function useRunScheduledBackup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const { data } = await http.post<BackupExecution>(`/badms/schedules/${id}/run/`);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: badmsKeys.all });
    },
  });
}

// Restorations
export function useRestorations() {
  return useQuery({
    queryKey: badmsKeys.restorations(),
    queryFn: async () => {
      const { data } = await http.get<{ count: number; results: RestorationRequest[] }>(
        "/badms/restorations/",
      );
      return data;
    },
  });
}

export function useSubmitRestoration() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: SubmitRestorationPayload) => {
      const { data } = await http.post<RestorationRequest>("/badms/restorations/", payload);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: badmsKeys.all });
    },
  });
}

export function useRestorationDecision() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, payload }: { id: number; payload: RestorationDecisionPayload }) => {
      const { data } = await http.post<RestorationRequest>(
        `/badms/restorations/${id}/decision/`,
        payload,
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: badmsKeys.all });
    },
  });
}

// Special Archival
export function useSpecialArchives() {
  return useQuery({
    queryKey: badmsKeys.specialArchives(),
    queryFn: async () => {
      const { data } = await http.get<{ count: number; results: SpecialArchivalRecord[] }>(
        "/badms/special-archives/",
      );
      return data;
    },
  });
}

export function useSubmitSpecialArchival() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: SubmitSpecialArchivalPayload) => {
      const { data } = await http.post<SpecialArchivalRecord>(
        "/badms/special-archives/",
        payload,
      );
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: badmsKeys.all });
    },
  });
}

// Audit Logs
export function useAuditLogs(filters?: { action?: string; target_type?: string; outcome?: string }) {
  return useQuery({
    queryKey: badmsKeys.auditLogs(filters as Record<string, string>),
    queryFn: async () => {
      const { data } = await http.get<{ count: number; results: BadmsAuditLog[] }>(
        "/badms/audit-logs/",
        { params: filters },
      );
      return data;
    },
  });
}

// Compliance Reports
export function useComplianceReport() {
  return useQuery({
    queryKey: badmsKeys.complianceReport(),
    queryFn: async () => {
      const { data } = await http.get<ComplianceSummary>("/badms/reports/summary/");
      return data;
    },
  });
}
