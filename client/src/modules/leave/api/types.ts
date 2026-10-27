export type LeaveCategory = "CL" | "RH" | "SCL" | "EL" | "COL" | "VL";

export type LeaveStatus =
  | "draft"
  | "awaiting_substitute"
  | "unit_head_queue"
  | "establishment"
  | "final_decision"
  | "approved"
  | "rejected"
  | "withdrawn"
  | "cancelled";

export interface LeaveBalance {
  id: number;
  user_id: number;
  year: number;
  category: LeaveCategory;
  allocated: number;
  used: number;
  pending: number;
  available: number;
}

export interface LeaveTransitionHistory {
  from_status: string;
  to_status: string;
  actor_user_id: number | null;
  reason: string;
  at: string;
}

export interface LeaveRequest {
  id: number;
  user_id: number;
  category: LeaveCategory;
  start_date: string;
  end_date: string;
  half_day: boolean;
  half_day_period: "none" | "FN" | "AN";
  days_count: number;
  purpose: string;
  station_leave: boolean;
  station_details: string;
  substitute_user_id: number | null;
  substitute_status: "none" | "pending" | "accepted" | "declined";
  substitute_remarks: string;
  unit_head_remarks: string;
  authority_remarks: string;
  rejection_reason: string;
  status: LeaveStatus;
  created_at: string;
  updated_at: string;
  transitions?: LeaveTransitionHistory[];
}

export interface LeaveApplyPayload {
  category: LeaveCategory;
  start_date: string;
  end_date: string;
  half_day?: boolean;
  half_day_period?: "none" | "FN" | "AN";
  purpose?: string;
  station_leave?: boolean;
  station_details?: string;
  substitute_user_id?: number | null;
}

export interface SubstituteActionPayload {
  accept: boolean;
  remarks?: string;
}

export interface LeaveTransitionPayload {
  to_status: LeaveStatus;
  reason?: string;
}
