/** Shapes the leave API returns. Field names match the DRF serializers
 *  exactly, so a rename on the server breaks the build rather than silently
 *  rendering `undefined`. */

export const LEAVE_CATEGORIES = [
  "CASUAL", "RH", "SCL", "EL", "COL", "VL",
] as const;
export type LeaveCategory = (typeof LEAVE_CATEGORIES)[number];

export const CATEGORY_LABELS: Record<string, string> = {
  CASUAL: "Casual Leave",
  RH: "Restricted Holiday",
  SCL: "Special Casual Leave",
  EL: "Earned Leave",
  COL: "Commuted Leave",
  VL: "Vacation Leave",
};

/** What each category counts against. Mirrors the server's counting rules; the
 *  server is authoritative and this is only for the hint under the date field. */
export const CONTINUOUS_CATEGORIES: LeaveCategory[] = ["EL", "COL", "VL"];
export const HALF_DAY_CATEGORIES: LeaveCategory[] = ["CASUAL"];
export const VACATION_ONLY: LeaveCategory[] = ["VL"];

export interface LeaveRequest {
  id: number;
  status: string;
  status_label: string;
  category: LeaveCategory;
  category_label: string;
  start_date: string;
  end_date: string;
  requested_days: string;
  half_day: boolean;
  half: string;
  half_day_allowed: boolean;
  purpose: string;
  station_leave_required: boolean;
  station_leave_details: string;
  substitute_required: boolean;
  kind: string;
  department: string;
  org_unit: number | null;
  org_unit_name: string;
  unit_head_recommendation: string;
  medical_evidence_reference: string;
  offline_sanction_reference: string;
  source: string;
  decided_by_user_id: number | null;
  decided_at: string | null;
  decision_note: string;
  created_at: string;
  updated_at: string;
}

export interface SubstituteNomination {
  id: number;
  leave_request: number;
  extension_request_id: number | null;
  nominee_user_id: number;
  status: "pending" | "accepted" | "declined" | "superseded" | "withdrawn";
  period_start: string;
  period_end: string;
  responded_at: string | null;
  created_at: string;
}

export interface ApprovalTask {
  id: number;
  leave_request_id: number;
  subject_type: "CW-EL-01" | "CW-EL-02" | "CW-EL-03" | "CW-EL-04";
  subject_id: number;
  kind: string;
  assignee_user_id: number;
  status: "pending" | "completed" | "cancelled";
  status_label: string;
  assigned_at: string;
  completed_at: string | null;
  reminder_due_at: string | null;
  escalation_due_at: string | null;
  reminder_sent_at: string | null;
  escalated_at: string | null;
  escalated_to_user_id: number | null;
  outcome: string;
  note: string;
}

export interface LeaveBalance {
  user_id: number;
  year: number;
  category: LeaveCategory;
  days: string;
  year_end_applied: boolean;
}

export interface LeaveLedgerEntry {
  id: number;
  user_id: number;
  year: number;
  category: LeaveCategory;
  category_label: string;
  kind: string;
  days: string;
  signed_days: string;
  note: string;
  leave_request_id: number | null;
  created_by_user_id: number | null;
  created_at: string;
}

export interface CancellationRequest {
  id: number;
  leave_request: number;
  status: string;
  reason: string;
  unit_head_recommendation: string;
  decided_by_user_id: number | null;
  decided_at: string | null;
  decision_note: string;
  created_at: string;
}

export interface ExtensionRequest {
  id: number;
  leave_request: number;
  status: string;
  additional_start_date: string;
  additional_end_date: string;
  additional_days: string;
  reason: string;
  substitute_required: boolean;
  unit_head_recommendation: string;
  decided_by_user_id: number | null;
  decided_at: string | null;
  decision_note: string;
  created_at: string;
}

export interface ResumptionRequest {
  id: number;
  leave_request: number;
  status: string;
  actual_resumption_date: string;
  details: string;
  adjustment_days: string;
  reviewed_by_user_id: number | null;
  reviewed_at: string | null;
  review_note: string;
  created_at: string;
}

export interface OrganizationalUnit {
  id: number;
  name: string;
  head_user_id: number | null;
  is_active: boolean;
}

export interface HierarchyRouteStep {
  id: number;
  kind: string;
  order: number;
  designation: string;
  user_id: number | null;
}

export interface HierarchyRoute {
  id: number;
  name: string;
  leave_category: string;
  org_unit: number | null;
  is_active: boolean;
  steps: HierarchyRouteStep[];
}

export interface SlaThresholdSerializer {
  id: number;
  task_kind: string;
  reminder_hours: number | null;
  escalate_hours: number | null;
  escalation_user_id: number | null;
  escalation_designation: string;
  escalation_changes_routing: boolean;
  is_active: boolean;
}

export interface LeavePolicySerializer {
  id: number;
  casual_days: string;
  restricted_holiday_days: string;
  special_casual_days: string;
  earned_days: string;
  vacation_days: string;
  commuted_days: string;
  vacation_to_earned_ratio: string;
  earned_carries_forward: boolean;
  commuted_carries_forward: boolean;
  earned_carry_forward_cap: string | null;
  commuted_carry_forward_cap: string | null;
  year_end_month: number;
  substitute_required_for: string[];
  establishment_step_enabled: boolean;
  category_kinds: Record<string, string[]>;
}

export interface CalendarSummary {
  effective_year: number | null;
  closed_holidays: [string, string][];
  restricted_holidays: [string, string][];
  vacation_periods: {
    label: string; start_date: string; end_date: string; year: number;
  }[];
}

export interface AdminConfig {
  policy: LeavePolicySerializer;
  units: OrganizationalUnit[];
  routes: HierarchyRoute[];
  thresholds: SlaThresholdSerializer[];
  calendar: CalendarSummary;
  unassigned_steps: string[];
}

export interface HolidayCalendarSerializer {
  id: number;
  year: number;
  status: string;
  is_effective: boolean;
  published_at: string | null;
  holidays: { id: number; date: string; name: string;
              is_restricted_holiday: boolean }[];
}

export interface VacationPeriodSerializer {
  id: number;
  label: string;
  start_date: string;
  end_date: string;
  year: number;
  source_reference: string;
}

export interface NotificationOutbox {
  id: number;
  topic: string;
  status: string;
  subject: string;
  recipient_user_id: number | null;
  recipient_email: string;
  sent_at: string | null;
  attempts: number;
  last_error: string;
  created_at: string;
}

export interface YearEndReport {
  report: string;
  year: number;
  credited: number;
  lapsed: number;
  converted: number;
  carried: number;
  skipped: number;
  exceptions: { user_id: number; error: string }[];
}

export interface BalanceAdjustment {
  user_id: number;
  year: number;
  category: LeaveCategory;
  days: string;
  kind?: "credit" | "debit" | "adjustment";
  note: string;
}

/** States that are still moving, so the UI can offer the action that fits. */
export const PENDING_STATES = [
  "awaiting_substitute_response", "applicant_action_required",
  "awaiting_unit_head_review", "awaiting_establishment_routing",
  "awaiting_final_sanction_decision", "awaiting_director_self_sanction",
] as const;

export const TERMINAL_STATES = ["rejected", "withdrawn", "cancelled"] as const;

export function isPending(status: string): boolean {
  return (PENDING_STATES as readonly string[]).includes(status);
}

export function isTerminal(status: string): boolean {
  return (TERMINAL_STATES as readonly string[]).includes(status);
}

/** Whether the owner may still cancel. BR-EL-023: only before it starts. */
export function canCancel(row: LeaveRequest): boolean {
  return row.status === "approved" && new Date(row.start_date) > new Date();
}

/** BR-EL-025: only Earned, Commuted and Vacation Leave can be extended. */
export function canExtend(row: LeaveRequest): boolean {
  return row.status === "approved"
    && ["EL", "COL", "VL"].includes(row.category);
}

export function canResume(row: LeaveRequest): boolean {
  return canExtend(row) && new Date(row.start_date) <= new Date();
}