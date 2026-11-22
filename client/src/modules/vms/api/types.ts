/** Wire types for the VMS API (`/api/v1/vms`). Shapes mirror the server's serializers;
 *  fields the screens do not read are left out on purpose. */

export interface CursorPage<T> {
  results: T[];
  next: string | null;
  previous: string | null;
}

export interface ResultList<T> {
  results: T[];
  count?: number;
}

// -- Notifications ---------------------------------------------------------------
export interface VmsNotification {
  id: number;
  topic: string;
  subject: string;
  body: string;
  created_at: string;
  read_at: string | null;
}

export interface Arrival {
  notification: VmsNotification;
  checked_in_at: string;
  request: Record<string, unknown> | null;
}

// -- Host approvals ------------------------------------------------------------------
export type RequestStatus =
  | "pending" | "awaiting_admin" | "approved" | "rejected" | "expired"
  | "completed" | "terminated";

export interface HostRequest {
  id: number;
  visitor_name: string;
  host_user_id: number;
  purpose: string;
  scheduled_start: string;
  scheduled_end: string;
  status: RequestStatus;
  source: string;
  is_urgent: boolean;
  requested_zones: number[];
  decision_note: string;
  decided_at: string | null;
  expires_at: string | null;
  created_at: string;
}

export type Decision = "approve" | "reject";

export interface BulkDecisionResult {
  id: number;
  ok: boolean;
  status?: string;
  error?: string;
}

// -- Gate ----------------------------------------------------------------------------
export interface GateFailure {
  code: string;
  rule: string;
  message: string;
}

export interface GateOutcome {
  detail: string;
  visitor_name?: string;
  vip_override?: boolean;
  visit_log_id?: number;
  code?: string;
  failures?: GateFailure[];
  override_eligible?: boolean;
}

export interface Denial {
  id: number;
  visit_pass_id: number;
  visitor_name: string;
  gate_id: number | null;
  failures: string[];
  overridden: boolean;
  escalated: boolean;
  created_at: string;
}

// -- Roster and monitor --------------------------------------------------------------
export interface OnSiteVisitor {
  pass_id: number;
  visitor_name: string;
  visitor_phone: string;
  visitor_email: string;
  zone_id: number | null;
  zone_name: string;
  last_seen_at: string | null;
  valid_until: string;
  terminated: boolean;
  overstay: boolean;
  host_user_id: number;
  host_name: string;
  host_department: string;
}

export interface Dashboard {
  on_site: number;
  by_zone: { zone_id: number | null; zone_name: string; count: number }[];
  by_department: { department: string; count: number }[];
  open_alerts: { total: number; by_kind: Record<string, number> };
  overstays: { count: number };
  as_of: string;
}

// -- Muster --------------------------------------------------------------------------
export interface Muster {
  id: number;
  status: "open" | "closed";
  trigger_role: string;
  triggered_by_user_id: number;
  triggered_at: string;
  closed_at: string | null;
  reason: string;
  counts: Record<string, number>;
}

export type RollCallStatus = "accounted" | "evacuated";

export interface MusterEntry {
  pass_id: number;
  visitor_name: string;
  last_zone_name: string;
  host_name: string;
  status: string;
}

// -- Events --------------------------------------------------------------------------
export interface VmsEvent {
  id: number;
  name: string;
  organizer: string;
  valid_from: string;
  valid_until: string;
  status: string;
  fast_lane: boolean;
  zone_ids: number[];
}

// -- Reports -------------------------------------------------------------------------
export interface ReportDef {
  key: string;
  title: string;
  params: string[];
  identity: boolean;
}

export interface ReportResult {
  columns: string[];
  rows: Record<string, unknown>[];
  truncated: boolean;
}

export type ExportFormat = "csv" | "pdf";

// -- Administration ------------------------------------------------------------------
export interface Policy {
  id: number;
  version: number;
  status: "draft" | "published" | "archived";
  published_at: string | null;
  visiting_hours_start: string;
  visiting_hours_end: string;
  max_visit_hours: number;
  walk_in_pass_hours: number;
  approval_timeout_hours: number;
  advance_registration_hours: number;
}

export interface BlacklistVersion {
  id: number;
  version: number;
  status: string;
  published_at: string | null;
}

export interface RoleAssignment {
  id: number;
  user_id: number;
  role: "admin" | "security";
  scope_type: "campus" | "zone" | "gate";
  scope_id: number | null;
  starts_at: string;
  ends_at: string;
  revoked_at: string | null;
}

export interface Zone {
  id: number;
  name: string;
  is_restricted: boolean;
  is_active: boolean;
}
