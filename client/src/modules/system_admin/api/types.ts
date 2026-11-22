/** TypeScript types for System Admin module. */

export type UserType = "student" | "faculty" | "staff";
export type UserStatus = "active" | "deactivated" | "archived";

export interface UserAccount {
  user_id: number;
  institute_id: string;
  username: string;
  email: string;
  user_type: UserType;
  name: string;
  contact_number: string;
  department: string;
  programme: string;
  discipline: string;
  batch_year: number | null;
  status: UserStatus;
  deactivated_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface RoleAssignment {
  id: number;
  role_code: string;
  role_name: string;
  user_id: number;
  status: "scheduled" | "active" | "expired" | "revoked";
  is_singular: boolean;
  start_date: string;
  end_date: string | null;
  scope: string;
  reason: string;
  assigned_by: number;
  created_at: string;
  updated_at: string;
}

export interface RoleDirectoryEntry {
  role_code: string;
  role_name: string;
  is_singular: boolean;
  category: string;
  active_holders_count: number;
  is_vacant: boolean;
  holders: Array<{
    assignment_id: number;
    user_id: number;
    start_date: string;
    end_date: string | null;
    scope: string;
  }>;
}

export interface ArchivedUserRecord {
  user_id: number;
  institute_id: string;
  username: string;
  email: string;
  user_type: string;
  reason: string;
  retention_option: string;
  archived_by: number;
  archived_at: string;
  reversible_until: string;
  is_permanent: boolean;
  snapshot: Record<string, unknown>;
  created_at: string;
}

export interface HistoricalDatasetArchive {
  id: number;
  category: string;
  description: string;
  date_range_start: string;
  date_range_end: string;
  record_count: number;
  backup_reference: string;
  archived_by: number;
  is_restored: boolean;
  created_at: string;
}

export interface PermanentPurgeRequest {
  id: number;
  dataset_identifier: string;
  requested_by: number;
  requested_at: string;
  retention_verified: boolean;
  reason: string;
  status: "pending_it_head" | "approved" | "rejected" | "purged";
  it_head_user_id: number | null;
  it_head_decided_at: string | null;
  it_head_remarks: string;
  created_at: string;
}

export interface SystemAuditLog {
  id: number;
  actor_id: number;
  action: string;
  target_id: string;
  ip_address: string | null;
  result: "success" | "failure";
  context: Record<string, unknown>;
  timestamp: string;
}

export interface FailedLoginLog {
  id: number;
  username: string;
  ip_address: string | null;
  attempted_at: string;
  reason: string;
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
    active_assignments: number;
    vacant_singular_roles: number;
    approaching_expiries_30d: number;
  };
  security: {
    failed_logins_24h: number;
    total_audit_events: number;
  };
  archives: {
    archived_users: number;
    pending_purge_authorizations: number;
  };
  system_health: {
    status: string;
    database: string;
    auth_service: string;
  };
}
