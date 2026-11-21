/** Types for System Admin module API.
 * Matching server serializers and DTO definitions.
 */

export type UserType = "student" | "faculty" | "staff";
export type UserStatus = "active" | "deactivated" | "archived";

export interface BasicUser {
  user_id: number;
  institute_id: string;
  user_type: UserType;
  email: string;
  first_name: string;
  last_name: string;
  contact_number?: string;
  department?: string;
  programme?: string;
  discipline?: string;
  batch_year?: number;
  employee_id?: string;
  date_of_joining?: string;
  expected_completion_date?: string;
  status: UserStatus;
  dashboard_access_enabled: boolean;
  deactivated_at?: string;
  deactivation_reason?: string;
  archived_at?: string;
  archival_reason?: string;
  reversible_until?: string;
  is_permanently_archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface RoleDefinition {
  id: number;
  code: string;
  name: string;
  description: string;
  module_association: string;
  department_association?: string;
  allowed_user_types: UserType[];
  is_singular: boolean;
  default_validity_days?: number;
  permissions: string[];
  conflict_role_codes: string[];
  is_system_role: boolean;
}

export type RoleAssignmentStatus = "scheduled" | "active" | "expired" | "revoked" | "reassigned";

export interface RoleAssignment {
  id: number;
  user_id: number;
  role: RoleDefinition;
  start_date: string;
  end_date?: string;
  scope_type: string;
  scope_id: string;
  reason?: string;
  status: RoleAssignmentStatus;
  assigned_by_user_id: number;
  assigned_at: string;
  effective_revoked_at?: string;
  revocation_reason?: string;
  pending_task_disposition?: "transfer" | "close";
  previous_holder_audit_until?: string;
}

export interface ArchivedRecord {
  id: number;
  category: string;
  identifier: string;
  data_payload: Record<string, unknown>;
  retention_until: string;
  backup_reference: string;
  archived_at: string;
  archived_by_user_id: number;
  reason?: string;
  status: "archived" | "restored" | "purge_requested" | "purged";
}

export interface PurgeRequest {
  id: number;
  archived_record: ArchivedRecord;
  requested_by_user_id: number;
  requested_at: string;
  reason: string;
  status: "pending_it_head" | "approved" | "rejected";
  it_head_user_id?: number;
  authorized_at?: string;
  rejection_reason?: string;
}

export interface AuditLog {
  id: number;
  timestamp: string;
  actor_user_id: number;
  actor_username: string;
  action: string;
  target_type: string;
  target_id: string;
  ip_address?: string;
  result: "success" | "failure";
  reason?: string;
  details?: Record<string, unknown>;
}

export interface DashboardMetrics {
  users: {
    total: number;
    active: number;
    deactivated: number;
    archived: number;
    by_type: Record<string, number>;
  };
  roles: {
    total_definitions: number;
    singular_definitions: number;
    active_assignments: number;
    scheduled_assignments: number;
    upcoming_expiries_30d: number;
  };
  archival: {
    archived_users: number;
    archived_data_records: number;
    pending_purge_authorizations: number;
  };
  security: {
    active_sessions: number;
    failed_logins_last_24h: number;
    consecutive_failed_login_alert: boolean;
    system_health: "nominal" | "warning";
  };
  recent_activity: {
    id: number;
    timestamp: string;
    actor_username: string;
    action: string;
    result: string;
    target_type: string;
    target_id: string;
  }[];
}

export interface SystemConfiguration {
  [key: string]: unknown;
}

export interface BulkOperationLog {
  batch_id: string;
  operation_type: string;
  total_records: number;
  successful_records: number;
  failed_records: number;
  initiated_by_user_id: number;
  summary: Record<string, unknown>;
  detailed_log: Array<{
    line?: number;
    user_id?: number;
    institute_id?: string;
    status: "created" | "updated" | "failed";
    reason?: string;
  }>;
  created_at: string;
}
