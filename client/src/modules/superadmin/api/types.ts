/** Super Admin API types. */

export type UserActivationStatus =
  | "ACTIVE"
  | "DEACTIVATED"
  | "ARCHIVED_REVERSIBLE"
  | "ARCHIVED_PERMANENT";

export type UserType = "STUDENT" | "FACULTY" | "STAFF";

export interface UserAccount {
  id: number;
  user_id: number;
  institute_id: string;
  email: string;
  user_type: UserType;
  activation_status: UserActivationStatus;
  deactivation_date: string | null;
  archival_date: string | null;
  reversibility_expires_at: string | null;
  department: string;
  program: string;
  batch: string;
  created_at: string;
  updated_at: string;
}

export type RoleAssignmentStatus =
  | "SCHEDULED"
  | "ACTIVE"
  | "EXTENDED"
  | "EXPIRED"
  | "REVOKED"
  | "REASSIGNED";

export interface RoleAssignment {
  id: number;
  user_id: number;
  role_name: string;
  scope_type: string;
  scope_id: string;
  valid_from: string;
  valid_to: string | null;
  status: RoleAssignmentStatus;
  is_singular: boolean;
  assigned_by_user_id: number;
  assignment_reason: string;
  created_at: string;
  updated_at: string;
}

export interface HistoricalArchive {
  id: number;
  entity_type: string;
  record_identifier: string;
  payload: Record<string, unknown>;
  backup_reference: string;
  retention_period_days: number;
  purge_eligible_at: string;
  status: "ARCHIVED" | "RESTORED" | "PURGED";
  archived_by_user_id: number;
  created_at: string;
}

export interface PurgeRequest {
  id: number;
  archive_record: number;
  requested_by_user_id: number;
  request_reason: string;
  status: "PENDING" | "AUTHORIZED" | "REJECTED" | "COMPLETED";
  authorized_by_user_id: number | null;
  authorized_at: string | null;
  rejection_reason: string;
  created_at: string;
}

export interface AuditLogEntry {
  id: number;
  event_type: string;
  actor_user_id: number;
  target_entity: string;
  target_id: string;
  ip_address: string | null;
  action_details: Record<string, unknown>;
  is_immutable: boolean;
  created_at: string;
}

export type AuditLog = AuditLogEntry;

export interface SystemParameter {
  id: number;
  parameter_key: string;
  parameter_value: Record<string, unknown>;
  version: number;
  effective_from: string;
  effective_to: string | null;
  is_active: boolean;
  updated_by_user_id: number;
  created_at: string;
}

export interface DashboardMetrics {
  total_users: number;
  active_users: number;
  deactivated_users: number;
  archived_reversible_users: number;
  archived_permanent_users: number;
}
