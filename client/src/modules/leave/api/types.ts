/** Wire shapes for the leave module. Mirrors modules/leave/api/serializers.py —
 *  a field added on one side and not the other shows up here as a type error
 *  rather than as `undefined` on a screen. */

export interface Page<T> {
  results: T[];
}

export type LeaveCategory = "cl" | "rh" | "scl" | "el" | "col" | "vl";

export interface LeaveTransition {
  id: number;
  from_status: string;
  to_status: string;
  action: string;
  actor_user_id: number | null;
  actor_role: string;
  actor_role_label: string;
  note: string;
  at: string;
}

export interface LeaveRequest {
  id: number;
  reference: string | null;
  kind: "new" | "extension" | "cancellation";
  kind_label: string;
  category: LeaveCategory;
  category_label: string;
  status: string;
  status_label: string;
  is_pending: boolean;
  user_id: number;
  period_from: string;
  period_to: string;
  half: "" | "first" | "second";
  days_counted: string;
  purpose: string;
  station_leave: Record<string, unknown>;
  substitute_user_id: number | null;
  substitute_required: boolean;
  recommendation: string;
  recommendation_note: string;
  decision_note: string;
  source: "online" | "offline";
  evidence_reference: string;
  base_request: number | null;
  route: { order: number; kind: string; authority: string; label: string }[];
  history?: LeaveTransition[];
}

export interface WorkflowTask {
  id: number;
  request_id: number;
  reference: string | null;
  category: LeaveCategory;
  period_from: string;
  period_to: string;
  days_counted: string;
  step_order: number;
  step_kind: string;
  task_class: string;
  authority: string;
  assignee_user_id: number | null;
  assignee_role: string;
  status: "pending" | "completed" | "cancelled";
  status_label: string;
  assigned_at: string;
  reminded_at: string | null;
  escalated_at: string | null;
  note: string;
}

export interface LeaveBalance {
  id: number;
  user_id: number;
  leave_year: number;
  category: LeaveCategory;
  category_label: string;
  entitled_days: string;
  carried_days: string;
  used_days: string;
  lapsed_days: string;
  available_days: string;
}

export interface LedgerEntry {
  id: number;
  user_id: number;
  category: LeaveCategory;
  leave_year: number;
  entry_type: string;
  days: string;
  request_id: number | null;
  note: string;
  at: string;
}

export interface SubstituteAssignment {
  id: number;
  request_id: number;
  reference: string | null;
  category: LeaveCategory;
  period_from: string;
  period_to: string;
  applicant_user_id: number;
  nominee_user_id: number;
  status: "nominated" | "accepted" | "declined" | "superseded";
  status_label: string;
  responded_at: string | null;
  response_note: string;
}

export interface LeaveResumption {
  id: number;
  request_id: number;
  reference: string | null;
  category: LeaveCategory;
  user_id: number;
  actual_date: string;
  approved_to: string;
  remarks: string;
  outcome: "pending" | "no_adjustment" | "early" | "late";
  outcome_label: string;
  reviewed_at: string | null;
  review_note: string;
}

export interface ValidationFailure {
  code: string;
  message: string;
  details?: unknown;
}

export interface ValidationResult {
  is_valid: boolean;
  chargeable_days: string;
  available_days: string;
  leave_year: number;
  employee_kind: string;
  charged: string[];
  skipped: string[];
  failures: ValidationFailure[];
}

export interface LeaveSummary {
  balances: LeaveBalance[];
  pending_requests: number;
  substitutions_awaiting_response: number;
  resumptions_pending: number;
  recent_requests: LeaveRequest[];
}

export interface LeavePolicy {
  id: number;
  leave_year: number;
  label: string;
  is_current: boolean;
  entitlements: Record<string, string>;
  continuous_counting: string[];
  half_day_categories: string[];
  vl_to_el_ratio: string;
  year_end_month: number;
  year_end_day: number;
  scl_admissibility_note: string;
}

export interface SlaThreshold {
  id: number;
  task_class: string;
  reminder_hours: number;
  escalation_hours: number;
  escalation_action: "notify" | "reassign";
  escalate_to_role: string;
  is_active: boolean;
}

export interface HolidayEntry {
  id: number;
  date: string;
  kind: "closed_holiday" | "restricted_holiday";
  label: string;
}

export interface HolidayCalendar {
  id: number;
  leave_year: number;
  label: string;
  published_at: string | null;
  is_effective: boolean;
  entries: HolidayEntry[];
}

export interface HierarchyRule {
  category: string;
  unit: string;
  designation: string;
  step_order: number;
  step_kind: string;
  authority: string;
  label: string;
  is_active: boolean;
}

export const CATEGORY_LABELS: Record<LeaveCategory, string> = {
  cl: "Casual Leave",
  rh: "Restricted Holiday",
  scl: "Special Casual Leave",
  el: "Earned Leave",
  col: "Commuted Leave",
  vl: "Vacation Leave",
};
