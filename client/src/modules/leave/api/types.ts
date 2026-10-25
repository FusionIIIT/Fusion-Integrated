export interface Page<T> {
  results: T[];
  next: string | null;
  previous: string | null;
}

export type LeaveStatus =
  | "pending" | "approved" | "rejected" | "cancelled" | "withdrawn";

export type HalfDay = "none" | "first" | "second";

export type SubstituteStatus = "none" | "pending" | "accepted" | "declined";

export type Recommendation = "none" | "recommended" | "not_recommended";

export type Stage = "unit_head" | "higher_sanction" | "director";

export interface LeaveType {
  id: number;
  code: string;
  name: string;
  max_days_per_year: number;
  requires_attachment: boolean;
  is_active: boolean;
  carry_forward: boolean;
  continuous_count: boolean;
  allow_half_day: boolean;
  requires_rh_calendar: boolean;
  requires_vacation_period: boolean;
}

export interface LeaveBalance {
  id: number;
  user_id: number;
  leave_type: number;
  leave_type_code: string;
  leave_type_name: string;
  year: number;
  allocated_days: number | string;
  used_days: number | string;
  remaining_days: number;
}

export interface LeaveRequest {
  id: number;
  user_id: number;
  leave_type: number;
  leave_type_code: string;
  leave_type_name: string;
  start_date: string;
  end_date: string;
  half_day: HalfDay;
  duration_days: number | string;
  reason: string;
  status: LeaveStatus;
  substitute_user_id: number | null;
  substitute_status: SubstituteStatus;
  unit_head_recommendation: Recommendation;
  current_stage: Stage;
  approver_user_id: number | null;
  rejection_reason: string;
  approved_at: string | null;
  created_at: string;
  is_extension: boolean;
  parent_request_id: number | null;
}

export interface LeaveApprovalInput {
  action: "approve" | "reject";
  remarks?: string;
}

export interface LeaveResumption {
  id: number;
  leave_request: number;
  actual_resumption_date: string;
  details: string;
  status: "pending" | "reviewed";
  reviewed_by_user_id: number | null;
  adjustment_days: number | string;
  reviewed_at: string | null;
  created_at: string;
}