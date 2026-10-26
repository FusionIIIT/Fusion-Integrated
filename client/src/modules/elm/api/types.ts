export interface LeaveBalance {
  id: number;
  user_id: number;
  leave_type: string;
  balance: number;
  updated_at: string;
}

export type LeaveStatus = "PENDING" | "APPROVED" | "REJECTED" | "CANCELLED";

export interface LeaveApplication {
  id: number;
  user_id: number;
  applicant_name: string;
  leave_type: string;
  start_date: string;
  end_date: string;
  reason: string;
  status: LeaveStatus;
  station_leave: boolean;
  substitute_user_id?: number | null;
  substitute_name?: string | null;
  reviewed_by_user_id?: number | null;
  review_remarks?: string;
  created_at: string;
  updated_at: string;
}

export interface ApplyLeavePayload {
  leave_type: string;
  start_date: string;
  end_date: string;
  reason: string;
  station_leave?: boolean;
  substitute_user_id?: number | null;
}

export interface ReviewLeavePayload {
  id: number;
  action: "APPROVED" | "REJECTED";
  remarks?: string;
}

export interface Holiday {
  id: number;
  date: string;
  description: string;
  is_rh: boolean;
}

