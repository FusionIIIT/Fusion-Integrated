export interface Page<T> {
  results: T[];
  next: string | null;
  previous: string | null;
}

export interface LeaveType {
  id: number;
  code: string;
  name: string;
  annual_quota: string;
  can_carry_forward: boolean;
  requires_substitute: boolean;
  is_active: boolean;
}

export interface LeaveBalance {
  id: number;
  user_id?: number;
  leave_type: LeaveType;
  year: number;
  allocated: string;
  used: string;
  pending: string;
  remaining: string;
}

export type LeaveApplicationStatus =
  | "pending"
  | "awaiting_substitute"
  | "applicant_action_required"
  | "awaiting_unit_head"
  | "awaiting_final_sanction"
  | "awaiting_director"
  | "recommended"
  | "approved"
  | "rejected"
  | "withdrawn"
  | "cancellation_pending_unit_head"
  | "cancellation_pending_final"
  | "cancelled";

export interface LeaveApplication {
  id: number;
  user_id: number;
  leave_type: LeaveType;
  start_date: string;
  end_date: string;
  half_day: boolean;
  station_leave: boolean;
  station_address: string;
  reason: string;
  substitute_user_id: number | null;
  substitute_status: string;
  status: LeaveApplicationStatus;
  reviewer_user_id: number | null;
  review_remarks: string;
  decided_at: string | null;
  total_days: string;
  original_application_id: number | null;
  is_extension: boolean;
  cancellation_status: string;
  cancellation_reason: string;
  cancellation_reviewer_user_id: number | null;
  cancellation_remarks: string;
  cancellation_decided_at: string | null;
  actual_resumption_date: string | null;
  resumption_status: string;
  resumption_reviewer_user_id: number | null;
  resumption_remarks: string;
  resumption_decided_at: string | null;
  resumption_days_adjusted: string;
  is_balance_refunded: boolean;
  is_offline: boolean;
  sanction_reference: string;
  sanction_date: string | null;
  sanction_authority_name: string;
  recommendation: string;
  created_at: string;
  updated_at?: string;
}

export interface HolidayItem {
  id: number;
  date: string;
  title: string;
  is_restricted: boolean;
}

export interface LeaveRolloverRecord {
  id: number;
  user_id: number;
  year: number;
  cl_lapsed: string;
  rh_lapsed: string;
  scl_lapsed: string;
  vl_converted: string;
  el_credited_from_vl: string;
  el_carried_forward: string;
  col_carried_forward: string;
  created_at: string;
}
