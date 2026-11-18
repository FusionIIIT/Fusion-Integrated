export interface Page<T> {
  results: T[];
  next: string | null;
  previous: string | null;
}

export type LeaveStatus = "pending" | "approved" | "rejected";

export interface LeaveType {
  id: number;
  name: string;
  max_days_per_year: number;
  carry_forward: boolean;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface LeaveBalance {
  id: number;
  user_id: number;
  leave_type: number;
  leave_type_name: string;
  year: number;
  total_days: number;
  used_days: number;
  remaining_days: number;
}

export interface LeaveRequest {
  id: number;
  employee_user_id: number;
  employee_name: string;
  leave_type: number;
  leave_type_name: string;
  start_date: string;
  end_date: string;
  reason: string;
  status: LeaveStatus;
  reviewed_by_user_id: number | null;
  reviewed_at: string | null;
  remarks: string;
  created_at: string;
  updated_at: string;
}

export interface ApplyLeavePayload {
  leave_type: number;
  start_date: string;
  end_date: string;
  reason: string;
}

export interface ReviewLeavePayload {
  action: "approve" | "reject";
  remarks?: string;
}
