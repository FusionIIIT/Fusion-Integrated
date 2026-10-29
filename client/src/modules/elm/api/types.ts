/** Wire types for the Employee Leave Management (ELM) API. */

export interface Page<T> {
  results: T[];
  count?: number;
  next: string | null;
  previous: string | null;
}

export type LeaveCategory = "CL" | "RH" | "SCL" | "EL" | "COL" | "VL";

export type LeaveStatus =
  | "draft"
  | "awaiting_substitute"
  | "awaiting_unit_head"
  | "awaiting_establishment"
  | "awaiting_sanction"
  | "approved"
  | "rejected"
  | "withdrawn"
  | "ongoing"
  | "cancel_requested"
  | "cancelled"
  | "extension_requested"
  | "extension_approved"
  | "resumption_submitted"
  | "resumption_reviewed";

export interface LeaveTransition {
  id: number;
  leave_request_id: number;
  from_status: LeaveStatus;
  to_status: LeaveStatus;
  actor_user_id: number | null;
  actor_role: string;
  reason: string;
  recommendation: string;
  at: string;
}

export interface LeaveRequest {
  id: number;
  user_id: number;
  category: LeaveCategory;
  status: LeaveStatus;
  request_type: "new" | "cancellation" | "extension" | "offline";
  start_date: string;
  end_date: string;
  half: "full" | "first_half" | "second_half";
  days_counted: string | number;
  purpose: string;
  station_leave_required: boolean;
  station_leave_address: string;
  substitute_id: number | null;
  substitute_accepted: boolean | null;
  unit_head_recommendation: string;
  parent_request_id?: number | null;
  offline_sanction_reference?: string;
  actual_resumption_date?: string | null;
  submitted_at: string | null;
  approved_at: string | null;
  created_at: string;
  updated_at?: string;
  transitions?: LeaveTransition[];
}

export interface LeaveBalance {
  id: number;
  user_id: number;
  category: LeaveCategory;
  year: number;
  credited: string | number;
  used: string | number;
  carried_forward: string | number;
  available: number;
}

export interface HolidayCalendar {
  id: number;
  date: string;
  name: string;
  holiday_type: "closed" | "restricted";
  year: number;
  is_published: boolean;
}

export interface ApplyLeavePayload {
  category: LeaveCategory;
  start_date: string;
  end_date: string;
  half?: "full" | "first_half" | "second_half";
  purpose?: string;
  substitute_id?: number | null;
  station_leave_required?: boolean;
  station_leave_address?: string;
  submit?: boolean;
}
