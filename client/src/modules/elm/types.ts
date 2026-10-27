/** Wire types and domain models for ELM frontend module. */

export type LeaveCategoryType = "CL" | "RH" | "SCL" | "EL" | "COL" | "VL";
export type HalfDayType = "none" | "first_half" | "second_half";
export type SubstituteStatusType = "none" | "pending" | "accepted" | "declined";
export type LeaveStatusType =
  | "pending_substitute"
  | "pending_unit_head"
  | "pending_estt"
  | "pending_sanction"
  | "approved"
  | "rejected"
  | "withdrawn"
  | "cancellation_pending"
  | "cancelled";

export interface LeaveBalance {
  id: number;
  user_id: number;
  year: number;
  category: LeaveCategoryType;
  credited: number;
  consumed: number;
  pending: number;
  carried_forward: number;
  available_balance: number;
}

export interface LeaveActionHistory {
  id: number;
  actor_id: number;
  action: string;
  previous_status: string;
  new_status: string;
  remarks: string;
  created_at: string;
}

export interface LeaveExtension {
  id: number;
  leave_request_id: number;
  start_date: string;
  end_date: string;
  duration_days: number;
  reason: string;
  substitute_user_id: number | null;
  substitute_status: SubstituteStatusType;
  status: "pending_substitute" | "pending_unit_head" | "pending_sanction" | "approved" | "rejected";
  unit_head_recommendation: string;
  remarks: string;
  created_at: string;
}

export interface LeaveResumption {
  id: number;
  leave_request_id: number;
  expected_date: string;
  actual_resumption_date: string;
  resumption_type: "normal" | "early" | "late";
  adjusted_duration_days: number;
  status: "submitted" | "reviewed";
  reviewer_id: number | null;
  reviewer_remarks: string;
  reviewed_at: string | null;
  created_at: string;
}

export interface LeaveRequest {
  id: number;
  user_id: number;
  category: LeaveCategoryType;
  start_date: string;
  end_date: string;
  half_day: HalfDayType;
  duration_days: number;
  purpose: string;
  is_station_leave: boolean;
  station_address: string;
  station_contact: string;
  station_start_date: string | null;
  station_end_date: string | null;
  substitute_user_id: number | null;
  substitute_status: SubstituteStatusType;
  substitute_remarks: string;
  substitute_acted_at: string | null;
  current_status: LeaveStatusType;
  current_assignee_role: string;
  unit_head_recommendation: "none" | "recommended" | "not_recommended";
  unit_head_remarks: string;
  unit_head_acted_at: string | null;
  sanctioning_authority_role: string;
  sanction_remarks: string;
  sanction_acted_at: string | null;
  final_decision_by_id: number | null;
  is_offline_sanctioned: boolean;
  offline_reference: string;
  created_at: string;
  updated_at: string;
  actions?: LeaveActionHistory[];
  extensions?: LeaveExtension[];
  resumption?: LeaveResumption | null;
}

export interface ApplyLeavePayload {
  category: LeaveCategoryType;
  start_date: string;
  end_date: string;
  purpose: string;
  half_day?: HalfDayType;
  is_station_leave?: boolean;
  station_address?: string;
  station_contact?: string;
  station_start_date?: string | null;
  station_end_date?: string | null;
  substitute_user_id?: number | null;
}

export interface HolidayItem {
  id: number;
  name: string;
  date: string;
  year: number;
  holiday_type: "closed" | "rh";
  is_published: boolean;
}

export interface AcademicVacationItem {
  id: number;
  name: string;
  start_date: string;
  end_date: string;
  academic_year: string;
  is_active: boolean;
}
