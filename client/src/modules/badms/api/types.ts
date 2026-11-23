export type DataClassification = "Routine" | "Sensitive" | "Critical" | "Archival";

export type BackupType = "manual" | "scheduled";

export type BackupStatus = "pending" | "running" | "success" | "failure";

export type ArchivalRequestStatus =
  | "submitted"
  | "hod_approved"
  | "hod_rejected"
  | "classified"
  | "encrypted"
  | "archived"
  | "special_archived";

export type StorageExtensionStatus = "submitted" | "approved" | "rejected";

export type RestorationStatus = "submitted" | "approved" | "rejected" | "restored" | "failed";

export interface BackupRecord {
  id: number;
  backup_type: BackupType;
  dataset_name: string;
  status: BackupStatus;
  started_at: string;
  completed_at: string | null;
  file_path: string;
  file_size_bytes: number;
  checksum_sha256: string;
  error_message: string;
  triggered_by_user_id: number | null;
  consecutive_failure_count: number;
  created_at: string;
}

export interface BackupSchedule {
  id: number;
  name: string;
  scope_type: "global" | "local";
  dataset_name: string;
  cron_expression: string;
  data_classification_filter: string;
  is_active: boolean;
  created_by_user_id: number;
  version: number;
  effective_from: string;
  effective_to: string | null;
  last_run_at: string | null;
  next_run_at: string | null;
  created_at: string;
}

export interface ArchivalRequest {
  id: number;
  requester_user_id: number;
  department: string;
  file_name: string;
  file_type: string;
  file_size_bytes: number;
  reason: string;
  file_storage_path: string;
  initial_classification: DataClassification;
  authoritative_classification: DataClassification | "";
  status: ArchivalRequestStatus;
  hod_reviewed_by_user_id: number | null;
  hod_decision_at: string | null;
  hod_remarks: string;
  sysadmin_classified_by_user_id: number | null;
  classified_at: string | null;
  encryption_algorithm: string;
  is_encrypted: boolean;
  encrypted_by_user_id: number | null;
  encrypted_at: string | null;
  is_special_archival: boolean;
  retention_policy_ref: string;
  created_at: string;
}

export interface StorageExtensionRequest {
  id: number;
  requester_user_id: number;
  department: string;
  current_usage_bytes: number;
  current_quota_bytes: number;
  requested_extension_bytes: number;
  justification: string;
  status: StorageExtensionStatus;
  hod_reviewed_by_user_id: number | null;
  hod_decision_at: string | null;
  hod_remarks: string;
  created_at: string;
}

export interface RestorationRequest {
  id: number;
  requester_user_id: number;
  department: string;
  archival_request_id: number;
  classification: DataClassification;
  target_destination: string;
  status: RestorationStatus;
  approved_by_user_id: number | null;
  approved_at: string | null;
  executed_by_user_id: number | null;
  restored_at: string | null;
  error_message: string;
  created_at: string;
}

export interface AuditEvent {
  id: number;
  event_type: string;
  actor_user_id: number;
  actor_role: string;
  target_model: string;
  target_id: number | null;
  department: string;
  details: Record<string, unknown>;
  ip_address: string | null;
  timestamp: string;
}

export interface SecurityPolicy {
  id: number;
  policy_key: string;
  policy_value: Record<string, unknown>;
  configured_by_user_id: number;
  effective_from: string;
  effective_to: string | null;
  is_active: boolean;
  created_at: string;
}

export interface DepartmentReport {
  department: string;
  total_archival_requests: number;
  archival_by_status: Record<string, number>;
  total_storage_extensions: number;
  storage_by_status: Record<string, number>;
}
