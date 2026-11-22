export interface LeaveType {
  code: string;
  name: string;
  is_active: boolean;
}

export interface LeaveBalance {
  employee_id: number;
  leave_type_code: string;
  year: number;
  entitled_days: string;
  used_days: string;
}

export interface LeaveApplication {
  id: number;
  applicant_id: number;
  leave_type_code: string;
  start_date: string;
  end_date: string;
  is_half_day: boolean;
  reason: string;
  substitute_id: number | null;
  status: "PENDING" | "APPROVED" | "REJECTED" | "WITHDRAWN" | "CANCELLED";
  submitted_at: string;
  decided_at: string | null;
  decided_by_id: number | null;
}
