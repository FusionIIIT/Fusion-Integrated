export type LeaveType = "CL" | "RH" | "SCL" | "EL" | "COL" | "VL";

export interface LeaveApplication {
  id: number;
  applicant_user_id: number;
  request_kind: "new" | "cancellation" | "extension";
  original_application: number | null;
  leave_type: LeaveType;
  start_date: string;
  end_date: string;
  requested_days: string;
  half_day_period: string;
  purpose: string;
  station_leave: boolean;
  station_leave_details: string;
  medical_evidence_reference: string;
  organizational_unit: string;
  status: string;
  substitute_required: boolean;
  substitute_user_id: number | null;
  recommendation: string;
  submitted_at: string | null;
  task_assigned_at: string | null;
  decided_at: string | null;
  created_at: string;
}

export interface LeaveBalance {
  leave_type: LeaveType;
  year: number;
  entitlement: string;
  available: string;
  carry_forward: boolean;
}

export interface LeaveTransaction {
  id: number;
  leave_type: LeaveType;
  year: number;
  amount: string;
  transaction_type: string;
  note: string;
  created_at: string;
}

export interface BalancesResponse {
  balances: LeaveBalance[];
  history: LeaveTransaction[];
}

export interface LeavePolicy {
  leave_type: LeaveType;
  annual_entitlement: string;
  applies_to: string;
  carry_forward: boolean;
  substitute_required: boolean;
  medical_evidence_required: boolean;
  higher_sanction: boolean;
}

export interface AuthorityRoute {
  id: number;
  unit_key: string;
  leave_type: LeaveType;
  unit_head_user_id: number;
  establishment_required: boolean;
  establishment_user_id: number | null;
  final_authority_user_id: number | null;
}

export interface CalendarDate {
  date: string;
  name: string;
  is_restricted_holiday: boolean;
}

export interface LeaveCalendar {
  id: number;
  name: string;
  effective_from: string;
  effective_to: string | null;
  is_published: boolean;
  is_current: boolean;
  dates: CalendarDate[];
}

export interface Resumption {
  id: number;
  application_id: number;
  actual_resumption_date: string;
  state: string;
  synchronization_status: string;
  synchronization_error: string;
}

export interface SlaConfiguration {
  task_kind: string;
  reminder_after_hours: number | null;
  escalation_after_hours: number | null;
  escalation_user_id: number | null;
}
