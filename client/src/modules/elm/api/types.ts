/* API types for ELM client module. */export type LeaveCategory = {
  code: string;
  label: string;
  entitlement_days: number;
  carry_forward: boolean;
  continuous_counting: boolean;
};

export type EmployeeLeaveBalance = {
  leave_category_code: string;
  leave_category_label: string;
  remaining_days: string;
  used_days: string;
  entitlement_days: number;
  carry_forward: boolean;
};

export type LeaveApplication = {
  id: number;
  user_id: number;
  leave_category_code: string;
  leave_category_label: string;
  requested_start: string; // ISO date string
  requested_end: string; // ISO date string
  purpose: string;
  halftype: string;
  station_leave: boolean;
  station_leave_details: string;
  status: string;
  created_at: string;
};

export type SubmitLeaveApplicationDTO = {
  leave_category_code: string;
  requested_start: string;
  requested_end: string;
  purpose: string;
  halftype?: string;
  station_leave: boolean;
  station_leave_details: string;
};
