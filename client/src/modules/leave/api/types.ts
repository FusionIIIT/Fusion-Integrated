/**
 * These are the wire shapes returned by the Django leave API; dates arrive as "YYYY-MM-DD" strings
 * and decimal amounts (days, balances) arrive as strings because Django serialises Decimal.
 */

export interface Page<T> {
  results: T[];
}

export type LeaveKind = "new" | "extension" | "cancellation" | "resumption";

export type LeaveStatus =
  | "draft" | "awaiting_substitute" | "applicant_action_required"
  | "awaiting_unit_head" | "awaiting_establishment" | "awaiting_final"
  | "awaiting_self_sanction" | "resumption_pending"
  | "approved" | "rejected" | "withdrawn" | "cancelled" | "resumed";

export type LeaveCategory = "cl" | "rh" | "scl" | "el" | "col" | "vl";

export type Half = "" | "first" | "second";

export interface LeaveRequest {
  id: number;
  kind: LeaveKind;
  kind_label: string;
  category: LeaveCategory;
  category_label: string;
  from_date: string;
  to_date: string;
  half: Half;
  days: string;
  purpose: string;
  status: LeaveStatus;
  station_leave_required: boolean;
  station_leave_details: string;
  parent: number | null;
  unit_head_user_id: number | null;
  final_authority: string;
  establishment_first: boolean;
  self_sanction: boolean;
  substitute_user_id: number | null;
  substitute_response: string;
  is_offline: boolean;
  sanction_reference: string;
  sanctioned_on: string | null;
  decision: string;
  decision_remarks: string;
  decided_at: string | null;
  created_at: string;
}

export interface LeaveBalance {
  category: LeaveCategory;
  category_label: string;
  opening: string;
  credited: string;
  used: string;
  available: string;
}

export interface BalanceResponse {
  year: string;
  results: LeaveBalance[];
}

export interface LeaveTask {
  task_id: number;
  stage: string;
  assigned_at: string;
  reminder_due_at: string | null;
  escalation_due_at: string | null;
  request: LeaveRequest;
}

export interface LeavePolicy {
  id: number;
  label: string;
  year_label: string;
  starts_on: string;
  ends_on: string;
  cl_days: number;
  rh_days: number;
  scl_days: number;
  el_days: number;
  vl_days: number;
  col_days: number;
  vl_per_el: number;
  authority_path: string;
  establishment_designation: string;
  establishment_step_enabled: boolean;
  reminder_hours: number;
  escalation_hours: number;
  year_end_on: string | null;
}

export interface CalendarEntry {
  id: number;
  date: string;
  ends_on: string | null;
  kind: string;
  label: string;
}

export interface LeaveCalendar {
  id: number;
  year_label: string;
  label: string;
  published_at: string | null;
  entries: CalendarEntry[];
}

export interface ApplyPayload {
  category: LeaveCategory;
  from_date: string;
  to_date: string;
  half?: Half;
  purpose: string;
  station_leave_required: boolean;
  station_leave_details?: string;
  substitute_user_id?: number | null;
  substitute_required: boolean;
}
