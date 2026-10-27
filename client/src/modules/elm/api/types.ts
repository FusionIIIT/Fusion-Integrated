export interface Page<T> {
  results: T[];
  next: string | null;
  previous: string | null;
}

export type LeaveCategory = "CL" | "RH" | "SCL" | "EL" | "COL" | "VL";
export type LeaveDayPart = "full_day" | "first_half" | "second_half";
export type LeaveStatus =
  | "pending" | "approved" | "rejected" | "cancelled" | "withdrawn";

export interface LeaveRequestEvent {
  event_type: "submitted" | "withdrawn";
  from_status: string;
  to_status: LeaveStatus;
  created_at: string;
}

export interface LeaveRequest {
  id: number;
  user_id: number;
  category: LeaveCategory;
  start_date: string;
  end_date: string;
  day_part: LeaveDayPart;
  reason: string;
  status: LeaveStatus;
  events: LeaveRequestEvent[];
  created_at: string;
  updated_at: string;
}

export interface LeaveRequestInput {
  category: LeaveCategory;
  start_date: string;
  end_date: string;
  day_part: LeaveDayPart;
  reason: string;
}
