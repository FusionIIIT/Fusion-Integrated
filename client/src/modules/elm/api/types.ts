export type LeaveType = "CL" | "RH" | "SCL" | "EL" | "COL" | "VL";

export type LeaveStatus =
  | "draft"
  | "submitted"
  | "pending_substitute"
  | "pending_unit_head"
  | "pending_sanction"
  | "approved"
  | "rejected"
  | "withdrawn"
  | "cancellation_requested"
  | "cancelled";

export type SubstituteStatus = "pending" | "accepted" | "declined";

export interface LeaveBalance {
  id: number;
  user_id: number;
  year: number;
  leave_type: LeaveType;
  allocated: string;
  used: string;
  balance: string;
  updated_at: string;
}

export interface LeaveAction {
  id: number;
  application: number;
  actor_id: number;
  action: string;
  comments: string;
  created_at: string;
}

export interface LeaveApplication {
  id: number;
  applicant_id: number;
  leave_type: LeaveType;
  start_date: string;
  end_date: string;
  reason: string;
  status: LeaveStatus;
  substitute_id?: number | null;
  substitute_status: SubstituteStatus;
  is_station_leave: boolean;
  station_address?: string;
  half_day: boolean;
  half_day_type?: string;
  unit_head_id?: number | null;
  unit_head_recommendation?: string;
  sanctioning_authority_id?: number | null;
  rejection_reason?: string;
  created_at: string;
  updated_at: string;
  actions: LeaveAction[];
  calculated_days: number;
}

export interface ApplyLeavePayload {
  leave_type: LeaveType;
  start_date: string;
  end_date: string;
  reason: string;
  substitute_id?: number | null;
  is_station_leave?: boolean;
  station_address?: string;
  half_day?: boolean;
  half_day_type?: string;
}
