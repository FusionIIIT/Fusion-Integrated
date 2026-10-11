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
  leave_type: LeaveType;
  year: number;
  allocated: string;
  used: string;
  pending: string;
  remaining: string;
}

export type LeaveApplicationStatus =
  | "pending"
  | "recommended"
  | "approved"
  | "rejected"
  | "withdrawn"
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
  created_at: string;
}

export interface HolidayItem {
  id: number;
  date: string;
  title: string;
  is_restricted: boolean;
}
