/** TypeScript type definitions for Employee Leave Management (ELM). */

export type LeaveCategory = "cl" | "rh" | "scl" | "el" | "col" | "vl";

export type LeaveStatus =
  | "draft"
  | "submitted"
  | "pending_substitute"
  | "substitute_declined"
  | "pending_unit_head"
  | "pending_sanction"
  | "awaiting_director_self_sanction"
  | "approved"
  | "rejected"
  | "withdrawn"
  | "cancellation_pending_unit_head"
  | "cancellation_pending_sanction"
  | "cancelled";

export type SubstituteStatus = "none" | "pending" | "accepted" | "declined";

export type UnitHeadRecommendation = "none" | "recommended" | "not_recommended";

export interface LeaveActionHistory {
  id: number;
  actor_id: number;
  action: string;
  from_status: string;
  to_status: string;
  remarks: string;
  created_at: string;
}

export interface LeaveRequest {
  id: number;
  user_id: number;
  category: LeaveCategory;
  start_date: string;
  end_date: string;
  half_day: boolean;
  half_day_type: "first_half" | "second_half" | null;
  leave_days: string | null;
  reason: string;
  is_station_leave: boolean;
  station_address: string;
  station_start_date: string | null;
  station_end_date: string | null;
  substitute_id: number | null;
  substitute_status: SubstituteStatus;
  substitute_remarks: string;
  status: LeaveStatus;
  unit_head_recommendation: UnitHeadRecommendation;
  unit_head_remarks: string;
  sanctioning_remarks: string;
  estimated_calendar_interval: number;
  actions?: LeaveActionHistory[];
  created_at: string;
  updated_at: string;
}

export interface LeaveBalance {
  id: number;
  user_id: number;
  category: LeaveCategory;
  year: number;
  credited: string;
  carried_forward: string;
  converted_in: string;
  availed: string;
  pending: string;
  converted_out: string;
  available: string;
  created_at: string;
  updated_at: string;
}

export interface Holiday {
  id: number;
  date: string;
  name: string;
  is_rh: boolean;
  is_closed: boolean;
}

export interface LeaveRequestCreatePayload {
  category: LeaveCategory;
  start_date: string;
  end_date: string;
  half_day?: boolean;
  half_day_type?: "first_half" | "second_half" | null;
  reason: string;
  is_station_leave?: boolean;
  station_address?: string;
  station_start_date?: string | null;
  station_end_date?: string | null;
  substitute_id?: number | null;
}
