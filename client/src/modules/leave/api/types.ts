/** Type definitions for the Leave (ELM) module. */

export type LeaveCategory = "CL" | "RH" | "SCL" | "EL" | "COL" | "VL";

export type LeaveStatus =
  | "DRAFT"
  | "AWAITING_SUBSTITUTE"
  | "SUBSTITUTE_DECLINED"
  | "AWAITING_UNIT_HEAD"
  | "AWAITING_ESTABLISHMENT"
  | "AWAITING_SANCTION"
  | "APPROVED"
  | "REJECTED"
  | "WITHDRAWN"
  | "AWAITING_CANCELLATION"
  | "CANCELLED";

export interface LeaveActionLog {
  id: number;
  actor_user_id: number;
  action: string;
  from_status: string;
  to_status: string;
  remarks: string;
  created_at: string;
}

export interface LeaveApplication {
  id: number;
  applicant_user_id: number;
  leave_type: LeaveCategory;
  start_date: string;
  end_date: string;
  half_day_type: "FULL" | "FIRST_HALF" | "SECOND_HALF";
  days_count: string;
  reason: string;
  status: LeaveStatus;
  substitute_user_id: number | null;
  substitute_status: "PENDING" | "ACCEPTED" | "DECLINED";
  substitute_remarks: string;
  is_station_leave: boolean;
  station_departure_date: string | null;
  station_arrival_date: string | null;
  station_address: string;
  contact_number: string;
  unit_head_user_id: number | null;
  unit_head_recommendation: string;
  unit_head_remarks: string;
  establishment_remarks: string;
  sanctioning_authority_user_id: number | null;
  sanction_decision: string;
  sanction_remarks: string;
  parent_leave_id: number | null;
  is_cancellation_requested: boolean;
  cancellation_reason: string;
  resumption_status: "NONE" | "SUBMITTED" | "REVIEWED";
  actual_resumption_date: string | null;
  resumption_remarks: string;
  resumption_days_adjusted: string;
  is_offline: boolean;
  offline_sanction_ref: string;
  offline_sanction_date: string | null;
  offline_sanctioned_by: string;
  created_at: string;
  updated_at: string;
  action_logs?: LeaveActionLog[];
}

export interface LeaveBalance {
  id: number;
  user_id: number;
  year: number;
  leave_type: LeaveCategory;
  credited: string;
  availed: string;
  balance: string;
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

export interface VacationItem {
  id: number;
  year: number;
  name: string;
  start_date: string;
  end_date: string;
  is_published: boolean;
}

export interface CreateLeavePayload {
  leave_type: LeaveCategory;
  start_date: string;
  end_date: string;
  half_day_type?: "FULL" | "FIRST_HALF" | "SECOND_HALF";
  reason: string;
  substitute_user_id?: number | null;
  is_station_leave?: boolean;
  station_departure_date?: string | null;
  station_arrival_date?: string | null;
  station_address?: string;
  contact_number?: string;
}
