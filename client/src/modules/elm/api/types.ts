/* API types for ELM client module. */export type LeaveCategory = {
  code: string;
  label: string;
  entitlement_days: number;
  carry_forward: boolean;
  continuous_counting: boolean;
};

export type EmployeeLeaveBalance = {
  user_id: number;
  leave_category_code: string;
  remaining_days: number;
  used_days: number;
};

export type LeaveApplication = {
  id: number;
  user_id: number;
  leave_category_code: string;
  requested_start: string; // ISO date string
  requested_end: string; // ISO date string
  purpose: string;
  halftype: string;
  station_leave: boolean;
  status: string;
  substitute_nominated?: number;
  substitute_accepted?: boolean;
  created_at: string;
};

export type SubmitLeaveApplicationDTO = {
  user_id: number;
  leave_category_code: string;
  requested_start: string;
  requested_end: string;
  purpose: string;
  halftype?: string;
  station_leave: boolean;
};