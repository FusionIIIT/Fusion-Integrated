export type LeaveType = "CL" | "RH" | "SCL" | "EL" | "COL" | "VL";

export type LeaveStatus =
  | "DRAFT"
  | "APPLICANT_ACTION"
  | "PENDING_SUBSTITUTE"
  | "PENDING_UNIT_HEAD"
  | "PENDING_AUTHORITY"
  | "APPROVED"
  | "REJECTED"
  | "WITHDRAWN"
  | "CANCELLED";

export type SubstituteStatus = "NOT_REQUIRED" | "PENDING" | "ACCEPTED" | "REJECTED";

export interface LeaveActionLog {
  id: string;
  actor_user_id: string;
  actor_role: string;
  action: string;
  remarks: string;
  created_at: string;
}

export interface LeaveBalance {
  id: string;
  user_id: string;
  leave_type: LeaveType;
  year: number;
  credited: number;
  availed: number;
  pending: number;
  balance: number;
}

export interface LeaveRequest {
  request_kind: "LEAVE" | "CANCEL" | "EXTEND" | "RESUME";
  original_id?: string;
  recommendation?: string;
  actual_end_date?: string;
  actual_duration_days?: string;
  id: string;
  applicant_user_id: string;
  leave_type: LeaveType;
  start_date: string;
  end_date: string;
  duration_days: number;
  is_half_day: boolean;
  half_day_session?: string;
  reason: string;
  station_leave: boolean;
  station_leave_address?: string;
  out_of_station_from?: string;
  out_of_station_to?: string;
  substitute_user_id?: string;
  substitute_status: SubstituteStatus;
  substitute_remarks?: string;
  status: LeaveStatus;
  current_approver_role?: string;
  rejection_reason?: string;
  created_at: string;
  updated_at: string;
  action_logs?: LeaveActionLog[];
}

export interface ApplyLeavePayload {
  leave_type: LeaveType;
  start_date: string;
  end_date: string;
  duration_days?: number;
  reason: string;
  is_half_day?: boolean;
  half_day_session?: string;
  station_leave?: boolean;
  station_leave_address?: string;
  out_of_station_from?: string;
  out_of_station_to?: string;
  substitute_id?: string;
  evidence_reference?: string;
}
