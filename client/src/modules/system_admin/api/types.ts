/** Wire types for the System Administrator (system_admin) API.
 *  Matches backend serializers in modules/system_admin/api/serializers.py.
 */

export interface Page<T> {
  results: T[];
  count?: number;
  next: string | null;
  previous: string | null;
}

export interface UserProfile {
  display_name: string;
  contact_number: string;
  department: string;
  programme: string;
  discipline: string;
  batch_year: number | null;
  employee_id: string;
  extra_attributes: Record<string, unknown>;
}

export type UserKind = "student" | "faculty" | "staff";
export type UserStatus = "active" | "deactivated" | "archived";

export interface AdminUser {
  id: number;
  username: string;
  institute_id: string;
  email: string;
  kind: UserKind;
  is_active: boolean;
  status: UserStatus;
  deactivated_at: string | null;
  date_of_joining: string | null;
  expected_completion_date: string | null;
  profile?: UserProfile;
  created_at: string;
  updated_at: string;
}

export type RoleCategory = "basic" | "rank" | "office" | "functional";
export type RoleAssignmentState =
  | "scheduled"
  | "active"
  | "extended"
  | "expired"
  | "revoked";

export interface RoleDefinition {
  code: string;
  label: string;
  category: RoleCategory;
  allowed_kinds: string[];
  is_singular: boolean;
  is_time_bound: boolean;
  default_lead_time_days: number;
  is_active: boolean;
  description: string;
  created_at: string;
}

export interface RoleAssignment {
  id: number;
  user_id: number;
  role_id: string;
  scope: string;
  start_date: string;
  end_date: string | null;
  state: RoleAssignmentState;
  assigned_by: number;
  reason: string;
  activated_at: string | null;
  expired_at: string | null;
  revoked_at: string | null;
  created_at: string;
}

export type ArchivalStatus =
  | "reversible"
  | "permanent_non_restorable"
  | "restored";

export interface ArchivedUserRecord {
  basic_user_id: number;
  institute_id: string;
  username: string;
  email: string;
  kind: UserKind;
  archived_at: string;
  reversible_until: string;
  status: ArchivalStatus;
  archival_reason: string;
  authorized_by: number;
  restored_at: string | null;
  user_data_snapshot: Record<string, unknown>;
}

export type PurgeRequestStatus =
  | "pending_it_head"
  | "approved"
  | "rejected"
  | "purged";

export interface PurgeRequest {
  id: number;
  archive_id: number;
  status: PurgeRequestStatus;
  requested_by: number;
  requested_at: string;
  request_reason: string;
  it_head_id: number | null;
  it_head_decision_at: string | null;
  it_head_comments: string;
  purged_at: string | null;
}

export interface AuditLog {
  id: number;
  timestamp: string;
  actor_id: number;
  actor_username: string;
  action: string;
  target_user_id: number | null;
  target_role_code: string | null;
  ip_address: string;
  user_agent: string;
  result: "success" | "failure" | "denied";
  reason: string;
  context_metadata: Record<string, unknown>;
}

export interface DashboardMetrics {
  users: {
    total: number;
    active: number;
    deactivated: number;
    archived: number;
    students: number;
    faculty: number;
    staff: number;
  };
  roles: {
    definitions: number;
    active_assignments: number;
    singular_roles: number;
  };
  archival: {
    reversible: number;
    permanent: number;
    pending_purge: number;
  };
  security: {
    failed_logins_24h: number;
    alerts: number;
  };
  timestamp: string;
}

export interface SystemParameter {
  key: string;
  value: string;
  description?: string;
  updated_at?: string;
}

export interface CreateUserPayload {
  user_kind: UserKind;
  name: string;
  institute_email: string;
  institute_id: string;
  contact_number?: string;
  department?: string;
  programme?: string;
  discipline?: string;
  batch_year?: number | null;
  employee_id?: string;
  date_of_joining?: string | null;
  expected_completion_date?: string | null;
  initial_password?: string;
}

export interface UpdateUserStatusPayload {
  new_status: UserStatus;
  reason: string;
}

export interface BulkStatusUpdatePayload {
  user_ids: number[];
  new_status: UserStatus;
  reason: string;
}

export interface AssignRolePayload {
  user_id: number;
  role_code: string;
  scope?: string;
  start_date: string;
  end_date?: string | null;
  reason: string;
}

export interface ReassignRolePayload {
  current_assignment_id: number;
  new_holder_id: number;
  effective_date: string;
  handover_tasks: boolean;
  audit_access_days: number;
  reason: string;
}

export interface RevokeRolePayload {
  assignment_id: number;
  is_emergency: boolean;
  effective_date: string;
  reason: string;
  pending_tasks_disposition?: "transfer" | "close";
  new_task_holder_id?: number | null;
}

export interface RequestPurgePayload {
  archive_id: number;
  reason: string;
}

export interface AuthorizePurgePayload {
  approved: boolean;
  comments?: string;
}
