/** Types for the Visitor Management System (VMS) client. */

export interface Visitor {
  id: number;
  name: string;
  email: string;
  phone: string;
  organization: string;
  id_document_type: string;
  id_document_number: string;
  is_vip: boolean;
  vip_reason: string;
  created_at: string;
}

export interface Pass {
  id: number;
  pass_number: string;
  qr_token: string;
  pass_type: "PRE_REGISTERED" | "WALK_IN" | "VIP" | "CONTRACTOR" | "EVENT";
  valid_from: string;
  valid_to: string;
  status: "ACTIVE" | "USED" | "EXPIRED" | "REVOKED";
  created_at: string;
}

export interface VisitRequest {
  id: number;
  visitor: Visitor;
  host_id: number;
  host_name: string;
  purpose: string;
  scheduled_start: string;
  scheduled_end: string;
  actual_check_in: string | null;
  actual_check_out: string | null;
  status:
    | "PENDING_APPROVAL"
    | "APPROVED"
    | "REJECTED"
    | "EXPIRED"
    | "CANCELLED"
    | "CHECKED_IN"
    | "CHECKED_OUT"
    | "AUTO_CHECKED_OUT"
    | "TERMINATED_EARLY";
  pass_type: string;
  access_zones: string[];
  admin_notes: string;
  rejection_reason: string;
  is_urgent_exception: boolean;
  extension_hours: number;
  external_event_ref: string;
  digital_pass: Pass | null;
  created_at: string;
}

export interface GateCheckLog {
  id: number;
  pass_number: string;
  gate_name: string;
  checkpoint_type: "ENTRY" | "EXIT" | "ZONE_CHECK";
  action: "CHECK_IN" | "CHECK_OUT" | "DENIED" | "OVERRIDE";
  operator_id: number | null;
  is_override: boolean;
  override_reason: string;
  is_offline_sync: boolean;
  timestamp: string;
}

export interface BlacklistEntry {
  id: number;
  name: string;
  id_document_type: string;
  id_document_number: string;
  phone: string;
  reason: string;
  status: "ACTIVE" | "SAFE_LISTED" | "INACTIVE";
  safe_list_until: string | null;
  safe_list_reason: string;
  safe_listed_by_id: number | null;
  created_at: string;
}

export interface EmergencyRosterItem {
  id: number;
  muster_id: string;
  assembly_point: string;
  initiated_by_id: number;
  initiated_at: string;
  visitor: Visitor;
  pass_record: Pass;
  check_in_time: string;
  accountability_status: "UNACCOUNTED" | "ACCOUNTED";
  accounted_at: string | null;
  notes: string;
}

export interface MusterResponse {
  summary: {
    total: number;
    accounted: number;
    unaccounted: number;
  };
  roster: EmergencyRosterItem[];
}

export interface DashboardMetrics {
  total_today: number;
  onsite_now: number;
  approved: number;
  pending: number;
  rejected: number;
  overstays: number;
  completed: number;
}

export interface AccessPolicy {
  id: number;
  version: number;
  visiting_hours_start: string;
  visiting_hours_end: string;
  max_duration_hours: number;
  is_published: boolean;
  published_at: string | null;
  policy_notes: string;
  created_at: string;
}

export interface PreAuthorization {
  id: number;
  host_id: number;
  visitor_email: string;
  visitor_name: string;
  valid_from: string;
  valid_to: string;
  is_active: boolean;
  created_at: string;
}
