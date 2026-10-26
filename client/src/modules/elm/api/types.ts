export interface LeaveType {
  code: string;
  name: string;
  is_active: boolean;
}

export interface LeaveBalance {
  employee: number;
  leave_type: string;
  year: number;
  entitled_days: string;
  used_days: string;
}

export interface LeaveApplication {
  id: number;
  applicant: number;
  leave_type: string;
  start_date: string;
  end_date: string;
  is_half_day: boolean;
  reason: string;
  substitute: number | null;
  status: "PENDING" | "APPROVED" | "REJECTED" | "WITHDRAWN" | "CANCELLED";
  submitted_at: string;
  decided_at: string | null;
  decided_by: number | null;
}
