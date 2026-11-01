/** TypeScript interfaces for System Admin module API. */

export interface BasicUser {
  id: number;
  internal_user_id: number;
  institute_id: string;
  institute_email: string;
  full_name: string;
  user_type: "student" | "faculty" | "staff";
  department: string;
  programme: string;
  discipline: string;
  batch_year: number | null;
  employee_id: string;
  date_of_joining: string;
  expected_completion_date: string | null;
  contact_number: string;
  status: "active" | "deactivated" | "archived";
  deactivated_at: string | null;
  deactivation_reason: string;
  created_at: string;
  updated_at: string;
}

export interface UserStatusHistoryEntry {
  id: number;
  from_status: string;
  to_status: string;
  changed_at: string;
  actor_username: string;
  reason: string;
}

export interface BasicUserDetail extends BasicUser {
  status_history: UserStatusHistoryEntry[];
  active_roles: {
    id: number;
    role_code: string;
    role_name: string;
    scope: string;
    start_date: string;
    end_date: string | null;
    status: string;
  }[];
}

export interface RoleConflictRule {
  id: number;
  conflicting_role_code: string;
  conflicting_role_name: string;
  reason: string;
}

export interface RoleHolderInfo {
  assignment_id: number;
  user_id: number;
  institute_id: string;
  full_name: string;
  start_date: string;
  end_date: string | null;
}

export interface RoleDefinitionItem {
  id: number;
  code: string;
  name: string;
  description: string;
  module_or_dept: string;
  allowed_user_types: string[];
  is_singular: boolean;
  is_time_bound: boolean;
  default_validity_days: number | null;
  permissions: string[];
  status: "available" | "deprecated";
  conflicts: RoleConflictRule[];
  current_holder: RoleHolderInfo | null;
  is_vacant: boolean;
  active_holders_count?: number;
  current_holders?: RoleHolderInfo[];
}

export interface RoleAssignmentItem {
  id: number;
  user: number;
  user_details: {
    id: number;
    institute_id: string;
    full_name: string;
    department: string;
    user_type: string;
  };
  role: number;
  role_details: {
    id: number;
    code: string;
    name: string;
    is_singular: boolean;
    module_or_dept: string;
  };
  scope: string;
  start_date: string;
  end_date: string | null;
  status: "scheduled" | "active" | "extended" | "expired" | "reassigned" | "revoked";
  assignment_reason: string;
  assigned_by: string;
  extended_at: string | null;
  extension_reason: string;
  revoked_at: string | null;
  revocation_reason: string;
  reassigned_to_user: number | null;
  reassignment_effective_date: string | null;
  previous_holder_audit_until: string | null;
  created_at: string;
}

export interface ArchivedUserItem {
  id: number;
  user: number;
  user_details: {
    id: number;
    institute_id: string;
    full_name: string;
    institute_email: string;
    user_type: string;
    department: string;
  };
  archival_date: string;
  archived_at: string;
  archived_by: string;
  reason: string;
  retention_option: string;
  reversibility_deadline: string;
  status: "reversible" | "permanent_non_restorable" | "restored";
  restored_at: string | null;
  restored_by: string;
  restoration_authorization_ref: string;
}

export interface ArchivedHistoricalDataItem {
  id: number;
  category: string;
  date_range_start: string;
  date_range_end: string;
  archived_at: string;
  archived_by: string;
  record_count: number;
  storage_size_kb: number;
  backup_reference: string;
  status: "archived" | "restored" | "purged";
  retention_expiry_date: string;
  summary_metadata: Record<string, unknown>;
  restored_at: string | null;
  restored_by: string;
  restoration_approval_ref: string;
}

export interface PermanentPurgeRequestItem {
  id: number;
  target_type: "historical_data" | "archived_user";
  target_summary: string;
  requested_by: string;
  requested_at: string;
  request_reason: string;
  regulatory_authorization_ref: string;
  status: "pending_it_head" | "approved" | "rejected";
  it_head_decided_by: string;
  it_head_decided_at: string | null;
  it_head_decision: string;
  it_head_comments: string;
  purge_executed_at: string | null;
}

export interface AuditLogItem {
  id: number;
  timestamp: string;
  actor_username: string;
  actor_role: string;
  action: string;
  target_user: string;
  target_role: string;
  ip_address: string | null;
  result: "SUCCESS" | "FAILURE" | "REJECTED";
  reason_or_context: string;
  metadata: Record<string, unknown>;
}

export interface SessionLogItem {
  id: number;
  session_id: string;
  username: string;
  ip_address: string | null;
  user_agent: string;
  started_at: string;
  last_activity_at: string;
  terminated_at: string | null;
  termination_reason: string;
  is_active: boolean;
}

export interface SecurityAlertItem {
  id: number;
  alert_type: string;
  severity: "INFO" | "WARNING" | "CRITICAL";
  message: string;
  trigger_count: number;
  target_username: string;
  source_ip: string | null;
  channels_dispatched: string[];
  dispatched_at: string;
  is_resolved: boolean;
}

export interface AdminNotificationItem {
  id: number;
  recipient_username: string;
  recipient_role: string;
  title: string;
  message: string;
  category: string;
  channel: string;
  status: string;
  is_read: boolean;
  created_at: string;
}

export interface ConfigItem {
  key: string;
  value: unknown;
  category: string;
  is_critical: boolean;
  type: string;
  description: string;
  updated_by: string;
}

export interface DashboardMetrics {
  users: {
    total: number;
    active: number;
    deactivated: number;
    archived: number;
    by_type: { user_type: string; count: number }[];
  };
  roles: {
    total_defined: number;
    active_assignments: number;
    vacant_singular_count: number;
    vacant_singular_roles: {
      id: number;
      code: string;
      name: string;
      module_or_dept: string;
    }[];
    expiring_soon_count: number;
  };
  archival: {
    reversible_users: number;
    permanent_users: number;
    historical_batches: number;
    pending_purge_requests: number;
  };
  security: {
    active_sessions: number;
    unresolved_alerts: number;
    recent_failures_24h: number;
    recent_actions: {
      id: number;
      timestamp: string;
      actor_username: string;
      action: string;
      target_user: string;
      target_role: string;
      result: string;
    }[];
  };
}

export interface AuditReportData {
  total_actions: number;
  success_count: number;
  failure_count: number;
  rejected_count: number;
  actions_breakdown: { action: string; count: number }[];
  top_actors: { actor_username: string; count: number }[];
}

export interface PageResponse<T> {
  results: T[];
  count: number;
}
