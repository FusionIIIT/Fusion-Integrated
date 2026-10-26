export type LeaveCategoryCode = "CL" | "RH" | "SCL" | "EL" | "COL" | "VL";

export interface LeaveType {
  id: number;
  code: LeaveCategoryCode | string;
  name: string;
  max_days_per_year: number;
  is_continuous_count: boolean;
  is_faculty_only: boolean;
  is_non_faculty_only: boolean;
  carries_forward: boolean;
  requires_document: boolean;
  is_active: boolean;
}

export interface LeaveBalance {
  id: number;
  leave_type: number;
  leave_type_code: string;
  leave_type_name: string;
  year: number;
  allotted: number;
  used: number;
  credited_from_vl: number;
  available: number;
}

export interface AuditTrailItem {
  id: number;
  actor_id: number;
  action: string;
  from_status: string;
  to_status: string;
  remarks: string;
  created_at: string;
}

export interface LeaveApplication {
  id: number;
  employee_id: number;
  leave_type: number;
  leave_type_code: string;
  leave_type_name: string;
  start_date: string;
  end_date: string;
  is_half_day: boolean;
  half_day_period: "NONE" | "FIRST_HALF" | "SECOND_HALF";
  days: number;
  reason: string;
  status:
    | "DRAFT"
    | "AWAITING_SUBSTITUTE"
    | "APPLICANT_ACTION_REQUIRED"
    | "AWAITING_UNIT_HEAD"
    | "AWAITING_ESTABLISHMENT"
    | "AWAITING_SANCTION"
    | "AWAITING_DIRECTOR_SELF_SANCTION"
    | "APPROVED"
    | "REJECTED"
    | "WITHDRAWN"
    | "CANCELLED";
  is_station_leave: boolean;
  station_destination: string;
  station_start_date: string | null;
  station_end_date: string | null;
  station_address: string;
  station_contact_no: string;
  substitute_id: number | null;
  substitute_status: "NONE" | "PENDING" | "ACCEPTED" | "DECLINED";
  substitute_declined_reason: string;
  substitute_responded_at: string | null;
  unit_head_id: number | null;
  unit_head_recommendation: "NONE" | "RECOMMENDED" | "NOT_RECOMMENDED" | "APPROVED" | "REJECTED";
  unit_head_remarks: string;
  unit_head_decided_at: string | null;
  establishment_id: number | null;
  establishment_remarks: string;
  establishment_routed_at: string | null;
  sanctioning_authority_id: number | null;
  sanctioning_authority_role: string;
  remarks: string;
  decided_at: string | null;
  audit_trail?: AuditTrailItem[];
  created_at: string;
  updated_at: string;
}

export interface HolidayItem {
  id: number;
  year: number;
  date: string;
  name: string;
  is_restricted_holiday: boolean;
  is_closed_holiday: boolean;
  is_published: boolean;
}

export interface ApplyInput {
  leave_type: number;
  start_date: string;
  end_date: string;
  reason: string;
  is_half_day?: boolean;
  half_day_period?: "NONE" | "FIRST_HALF" | "SECOND_HALF";
  is_station_leave?: boolean;
  station_destination?: string;
  station_start_date?: string | null;
  station_end_date?: string | null;
  station_address?: string;
  station_contact_no?: string;
  substitute_id?: number | null;
}

/** Actionable workflow task kinds — mirrors modules/elm/domain/sla.py TaskKind. */
export type TaskKind =
  | "SUBSTITUTE_RESPONSE"
  | "UNIT_HEAD_REVIEW"
  | "ESTABLISHMENT_ROUTING"
  | "SANCTION_DECISION"
  | "DIRECTOR_SELF_SANCTION"
  | "CANCELLATION_UNIT_HEAD"
  | "CANCELLATION_SANCTION"
  | "EXTENSION_UNIT_HEAD"
  | "EXTENSION_SANCTION"
  | "RESUMPTION_REVIEW";

export const TASK_KINDS: TaskKind[] = [
  "SUBSTITUTE_RESPONSE",
  "UNIT_HEAD_REVIEW",
  "ESTABLISHMENT_ROUTING",
  "SANCTION_DECISION",
  "DIRECTOR_SELF_SANCTION",
  "CANCELLATION_UNIT_HEAD",
  "CANCELLATION_SANCTION",
  "EXTENSION_UNIT_HEAD",
  "EXTENSION_SANCTION",
  "RESUMPTION_REVIEW",
];

/** Reminder/escalation thresholds for one task kind (BR-EL-038). */
export interface SlaConfiguration {
  id: number;
  task_kind: TaskKind | string;
  reminder_hours: number;
  escalation_hours: number;
  escalation_role: string;
  escalation_recipient_id: number | null;
  escalation_changes_routing: boolean;
  is_active: boolean;
  updated_by_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface SlaConfigurationInput {
  task_kind: TaskKind | string;
  reminder_hours: number;
  escalation_hours: number;
  escalation_role?: string;
  escalation_recipient_id?: number | null;
  escalation_changes_routing?: boolean;
  is_active?: boolean;
}

export interface WorkflowTaskItem {
  id: number;
  application: number | null;
  application_ref: string;
  subject_type: string;
  subject_id: number | null;
  task_kind: TaskKind | string;
  assignee_id: number;
  status: "OPEN" | "CLOSED";
  is_pending: boolean;
  opened_at: string;
  closed_at: string | null;
  closed_reason: string;
  reminded_at: string | null;
  escalated_at: string | null;
  escalated_to_id: number | null;
}

export interface SlaEventItem {
  id: number;
  task_id: number;
  task_kind: TaskKind | string;
  action: "NONE" | "REMIND" | "ESCALATE";
  reason: string;
  recipient_id: number | null;
  escalation_role: string;
  changes_routing: boolean;
  hours_elapsed: number;
  evaluated_at: string;
}

export interface SlaRunCounters {
  evaluated: number;
  reminded: number;
  escalated: number;
  rerouted: number;
  suppressed: number;
}

export interface NotificationItem {
  id: number;
  recipient_id: number;
  kind: "TASK_ASSIGNED" | "SLA_REMINDER" | "SLA_ESCALATION" | "DECISION_RECORDED" | string;
  subject: string;
  body: string;
  link: string;
  task_kind: string;
  task_id: number | null;
  read_at: string | null;
  created_at: string;
}

export interface NotificationFeed {
  unread_count: number;
  results: NotificationItem[];
}
