export interface LeaveType {
  code: string;
  label: string;
}

export type LeaveStatus = "pending" | "approved" | "rejected" | "withdrawn";

export interface LeaveApplication {
  id: number;
  leave_type: string;
  leave_type_label: string;
  start_date: string;
  end_date: string;
  days_requested: number;
  reason: string;
  status: LeaveStatus;
  created_at: string;
  updated_at: string;
}

export interface Page<T> {
  results: T[];
  next: string | null;
  previous: string | null;
}

export interface CreateLeaveApplication {
  leave_type: string;
  start_date: string;
  end_date: string;
  reason: string;
}
