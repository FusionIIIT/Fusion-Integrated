export interface LeaveType {
  id: number;
  code: string;
  name: string;
  annual_allowance: string;
}

export interface LeaveBalance {
  id: number;
  leave_type: number;
  leave_type_name: string;
  year: number;
  allocated_days: string;
  carried_days: string;
  available_days: string;
}

export interface LeaveRequest {
  id: number;
  leave_type: number;
  leave_type_name: string;
  start_date: string;
  end_date: string;
  days: number;
  reason: string;
  user_id: number;
  status: "pending" | "approved" | "rejected" | "cancelled";
  review_note: string;
  created_at: string;
}

export interface MyLeave {
  balances: LeaveBalance[];
  requests: LeaveRequest[];
  leave_types: LeaveType[];
}
