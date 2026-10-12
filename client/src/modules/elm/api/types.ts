/** Wire types for the ELM API. Decimals arrive as strings. */
export type Id = number;

export interface Page<T> {
  results: T[];
  next: string | null;
  previous: string | null;
}

export type LeaveKind = "new" | "cancellation" | "extension";
export type LeaveCategory = "CL" | "RH" | "SCL" | "EL" | "COL" | "VL";
export type LeaveHalf = "first" | "second" | "";
export type LeaveStatus =
  | "draft" | "awaiting_substitute" | "applicant_action_required"
  | "awaiting_unit_head" | "awaiting_establishment"
  | "awaiting_final_sanction" | "awaiting_director_sanction"
  | "approved" | "rejected" | "withdrawn" | "cancelled";
export type Decision = "approve" | "reject" | "recommended" | "not_recommended";

export interface LeaveRequest {
  id: Id;
  applicant: Id;
  kind: LeaveKind;
  category: LeaveCategory;
  start_date: string;
  end_date: string;
  half_day: LeaveHalf;
  days: string;
  purpose: string;
  station_leave: boolean;
  station_place: string;
  station_contact: string;
  status: LeaveStatus;
  substitute_user_id: Id | null;
  original: Id | null;
  department: string;
  final_decision: string;
  decided_by_user_id: Id | null;
  decided_at: string | null;
  rejection_reason: string;
  is_offline: boolean;
  sanction_reference: string;
  created_at: string;
}

export interface WorkflowTask {
  id: Id;
  request: Id;
  task_type: "substitute" | "unit_head" | "establishment"
    | "final_sanction" | "director_sanction" | "resumption";
  role: string;
  assigned_to_user_id: Id | null;
  status: "pending" | "done" | "skipped";
  decision: string;
  acted_at: string | null;
  created_at: string;
}

export interface SubstituteAssignment {
  id: Id;
  request: Id;
  substitute_user_id: Id;
  responsibility_start: string;
  responsibility_end: string;
  status: "pending" | "accepted" | "declined";
  decline_reason: string;
  responded_at: string | null;
  created_at: string;
}

export interface LeaveAccount {
  id: Id;
  user_id: Id;
  category: LeaveCategory;
  year: number;
  balance: string;
  used: string;
  lapsed: string;
}

export interface LeaveTransaction {
  id: Id;
  account: Id;
  kind: string;
  amount: string;
  balance_after: string;
  note: string;
  request_id: Id | null;
  actor_user_id: Id | null;
  created_at: string;
}

export interface Holiday {
  id: Id;
  date: string;
  kind: "closed" | "restricted";
  name: string;
}

export interface HolidayCalendar {
  id: Id;
  name: string;
  year: number;
  is_published: boolean;
  published_at: string | null;
  holidays: Holiday[];
  created_at: string;
}

export interface VacationPeriod {
  id: Id;
  label: string;
  start_date: string;
  end_date: string;
  academic_year: string;
  created_at: string;
}

export interface LeaveTypeConfig {
  id: Id;
  category: LeaveCategory;
  label: string;
  employee_kind: string;
  annual_entitlement: string;
  carry_forward: boolean;
  continuous: boolean;
  half_day: boolean;
  requires_substitute: boolean;
  requires_resumption: boolean;
  allows_extension: boolean;
  unit_head_final: boolean;
  requires_medical_evidence: boolean;
  active: boolean;
}

export interface SlaConfig {
  id: Id;
  task_type: string;
  reminder_hours: number;
  escalation_hours: number;
  escalate_to_designation: string;
  change_routing: boolean;
  active: boolean;
}
