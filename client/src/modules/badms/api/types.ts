export interface BackupRun {
  id: number;
  dataset_key: string;
  trigger: "manual" | "scheduled";
  status: "queued" | "running" | "succeeded" | "failed";
  started_at: string | null;
  finished_at: string | null;
  checksum_sha256: string;
  size_bytes: number;
  created_at: string;
}

export interface BackupSchedule {
  id: number;
  scope: "local" | "global";
  dataset_key: string;
  cron_expression: string;
  timezone: string;
  classification_filters: string[];
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface ArchiveRequest {
  id: number;
  file_name: string;
  data_date: string;
  owners: string;
  file_type: string;
  reason: string;
  department_code: string;
  special_operation: boolean;
  initial_classification: string;
  classification: string;
  status: string;
  decision_reason: string;
  created_at: string;
  updated_at: string;
}

export interface RestoreRequest {
  id: number;
  archive: number;
  archive_classification: string;
  file_name: string;
  reason: string;
  status: string;
  decision_at: string | null;
  created_at: string;
}

export interface StorageExtension {
  id: number;
  current_usage_bytes: number;
  quota_bytes: number;
  requested_bytes: number;
  justification: string;
  status: string;
  decision_reason: string;
  created_at: string;
}

export interface AuditEvent {
  id: number;
  actor_user_id: number | null;
  action: string;
  resource: string;
  resource_id: string;
  outcome: string;
  details: Record<string, unknown>;
  occurred_at: string;
}

export interface SecurityPolicy {
  id: number;
  classification: string;
  effective_from: string;
  retention_days: number | null;
  encryption_required: boolean;
  created_by_user_id: number;
  created_at: string;
}

export interface BadmsReport {
  archives_by_status: Record<string, number>;
  backups_by_status: Record<string, number>;
  storage_extensions_by_status: Record<string, number>;
  generated_at: string;
}
