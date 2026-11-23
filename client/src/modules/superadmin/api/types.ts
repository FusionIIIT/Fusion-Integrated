/** TypeScript shapes for the superadmin API responses aligned with openapi/fusion-integrated.v1.yaml */

export interface Page<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export type ArchivalStatus = "reversible" | "restored" | "finalized_permanent";
export type PurgeStatus = "pending_it_head" | "approved" | "rejected" | "purged" | "expired";

export interface ArchivedUser {
  user_id: number;
  institute_id: string;
  username: string;
  email: string;
  user_kind: string;
  status: ArchivalStatus;
  archived_at: string;
  reversible_until: string;
  authorized_by: number;
  archival_reason: string;
  restored_at: string | null;
  restored_by: number | null;
  restoration_reason: string;
  finalized_permanent_at: string | null;
  metadata_snapshot?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface HistoricalArchive {
  id: number;
  dataset_category: string;
  title: string;
  date_range_start: string;
  date_range_end: string;
  record_count: number;
  backup_file_path: string;
  backup_checksum: string;
  retention_expires_at: string;
  is_restored: boolean;
  restored_at: string | null;
  is_purged: boolean;
  archived_by: number;
  summary_metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface PurgeRequest {
  id: number;
  archive: number;
  archive_title: string;
  dataset_category: string;
  status: PurgeStatus;
  requested_by: number;
  requested_at: string;
  request_reason: string;
  it_head_id: number | null;
  it_head_decision_at: string | null;
  it_head_comments: string;
  purged_at: string | null;
  execution_summary?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface PolicyParameter {
  id: number;
  key: string;
  value: string;
  value_type: string;
  version: number;
  effective_from: string;
  effective_to: string | null;
  description: string;
  updated_by: number;
  created_at: string;
  updated_at: string;
}

export interface AuditLog {
  id: number;
  timestamp: string;
  actor_id: number;
  actor_username: string;
  actor_role: string;
  action: string;
  target_id: string;
  target_type: string;
  result: string;
  ip_address: string | null;
  user_agent: string;
  reason: string;
  context_metadata?: Record<string, unknown>;
}

export interface DashboardSummary {
  archived_users_reversible: number;
  archived_users_total: number;
  purge_requests_pending: number;
  audit_logs_total: number;
}

/** Backward compatibility alias */
export type DashboardMetrics = DashboardSummary;
