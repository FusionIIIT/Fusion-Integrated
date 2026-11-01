export interface LeaveDecision {
  actor_user_id: number | null;
  actor_role: string;
  action: string;
  from_status: string;
  to_status: string;
  comment: string;
  created_at: string;
}

export interface LeaveRequest {
  id: number;
  employee_id: number;
  employee_name: string;
  policy: number;
  parent: number | null;
  request_kind: "new" | "cancellation" | "extension" | "offline";
  leave_type: string;
  start_date: string;
  end_date: string;
  charged_days: string;
  reason: string;
  station_leave_details: string;
  substitute_id: number | null;
  half_day: boolean;
  status: string;
  assigned_role: string;
  actual_resume_date: string | null;
  actual_resume_details: string;
  final_decision: string;
  final_decision_at: string | null;
  requires_higher_sanction: boolean;
  establishment_required: boolean;
  decisions: LeaveDecision[];
  created_at: string;
}

export interface LeaveBalance {
  id: number;
  user_id: number;
  policy: number;
  leave_type: string;
  leave_year: number;
  opening_balance: string;
  credited: string;
  used: string;
  available: string;
}

export interface LeaveLedgerEntry {
  id: number;
  request_id: number | null;
  entry_type: string;
  days: string;
  description: string;
  created_at: string;
}

export interface LeavePolicy {
  id: number;
  leave_type: string;
  leave_year: number;
  enabled: boolean;
  annual_entitlement: string;
  carry_forward_limit: string;
  year_end_treatment: "lapse" | "carry_forward" | "convert_to_el";
  conversion_ratio: string;
  max_continuous_days: number | null;
  requires_substitute: boolean;
  requires_higher_sanction: boolean;
  faculty_only: boolean;
  hierarchy: Record<string, unknown>;
  unit_head_sla_hours: number;
  final_sanction_sla_hours: number;
  escalation_role: string;
}

export interface LeaveHoliday {
  id: number;
  leave_year: number;
  day: string;
  name: string;
  restricted: boolean;
  published: boolean;
}

export interface CursorPage<T> {
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface LeaveTaskNotice {
  id: number;
  request_id: number;
  event: "assigned" | "reminder" | "escalated" | "decision";
  message: string;
  created_at: string;
  read_at: string | null;
}