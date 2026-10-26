/** Leave Management API types. */
export type LeaveCategory = "CL" | "RH" | "SCL" | "EL" | "VL" | "COL";
export type LeaveStatus =
  | "draft"
  | "submitted"
  | "substitute_pending"
  | "unit_head_review"
  | "establishment_review"
  | "final_sanction"
  | "approved"
  | "rejected"
  | "withdrawn"
  | "cancelled"
  | "extension_requested"
  | "resumption_pending"
  | "resumed";
export type EmployeeType = "faculty" | "non_faculty";

export interface LeavePolicy {
  id: number;
  category: LeaveCategory;
  employee_type: EmployeeType;
  annual_entitlement: string;
  carries_forward: boolean;
  half_day_allowed: boolean;
  requires_medical_certificate: boolean;
  max_per_request: string | null;
  effective_from: string;
  effective_to: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface HolidayCalendar {
  id: number;
  date: string;
  name: string;
  is_restricted: boolean;
  year: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface LeaveBalance {
  id: number;
  user_id: number;
  category: LeaveCategory;
  year: number;
  opening_balance: string;
  credited: string;
  availed: string;
  lapsed: string;
  closing_balance: string;
  created_at: string;
  updated_at: string;
}

export interface LeaveRequestTransition {
  id: number;
  from_status: LeaveStatus;
  to_status: LeaveStatus;
  actor_user_id: number | null;
  actor_role: string;
  reason: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface SubstituteRequest {
  id: number;
  leave_request: number;
  leave_request_category: LeaveCategory;
  leave_request_status: LeaveStatus;
  leave_request_start: string;
  leave_request_end: string;
  substitute_id: number;
  nominated_by: number;
  status: "pending" | "accepted" | "declined";
  responded_at: string | null;
  reason: string;
  created_at: string;
  updated_at: string;
}

export interface LeaveRequest {
  id: number;
  user_id: number;
  category: LeaveCategory;
  start_date: string;
  end_date: string;
  half_day: boolean;
  half_day_session: string;
  total_days: string;
  purpose: string;
  station_leave: boolean;
  station_leave_address: string;
  substitute_id: number | null;
  status: LeaveStatus;
  medical_certificate: string | null;
  unit_head_id: number | null;
  unit_head_remark: string;
  unit_head_action_at: string | null;
  establishment_id: number | null;
  establishment_remark: string;
  establishment_action_at: string | null;
  final_authority_id: number | null;
  final_authority_remark: string;
  final_authority_action_at: string | null;
  applied_at: string | null;
  approved_at: string | null;
  rejected_at: string | null;
  extension_of: number | null;
  extension_of_category: LeaveCategory | null;
  original_request: number | null;
  original_request_category: LeaveCategory | null;
  resumption_date: string | null;
  resumption_verified_by: number | null;
  resumption_verified_at: string | null;
  transitions: LeaveRequestTransition[];
  substitute_requests: SubstituteRequest[];
  created_at: string;
  updated_at: string;
}

export interface LeaveRequestListItem {
  id: number;
  user_id: number;
  category: LeaveCategory;
  start_date: string;
  end_date: string;
  half_day: boolean;
  total_days: string;
  purpose: string;
  station_leave: boolean;
  substitute_id: number | null;
  status: LeaveStatus;
  applied_at: string | null;
  approved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Page<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface LeaveRequestCreate {
  category: LeaveCategory;
  start_date: string;
  end_date: string;
  half_day: boolean;
  half_day_session: "forenoon" | "afternoon" | "";
  purpose: string;
  station_leave: boolean;
  station_leave_address: string;
  substitute_id: number | null;
}

export interface LeaveRequestModify {
  start_date?: string;
  end_date?: string;
  half_day?: boolean;
  half_day_session?: "forenoon" | "afternoon" | "";
  purpose?: string;
  station_leave?: boolean;
  station_leave_address?: string;
  substitute_id?: number | null;
}

export interface LeaveRequestWithdraw {
  reason?: string;
}

export interface LeaveRequestCancel {
  reason?: string;
}

export interface LeaveRequestExtend {
  end_date: string;
  purpose: string;
}

export interface LeaveRequestResume {
  resumption_date: string;
}

export interface SubstituteRequestRespond {
  accept: boolean;
  reason?: string;
}

export interface UnitHeadReview {
  recommend: boolean;
  remark?: string;
}

export interface EstablishmentReview {
  action: "forward" | "return";
  remark?: string;
}

export interface FinalSanction {
  approve: boolean;
  remark?: string;
}

export interface OfflineLeaveEntry {
  id: number;
  user_id: number;
  category: LeaveCategory;
  start_date: string;
  end_date: string;
  total_days: string;
  sanction_order_number: string;
  sanction_order_date: string;
  sanctioning_authority: string;
  remarks: string;
  entered_by: number;
  verified: boolean;
  verified_by: number | null;
  verified_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface LeaveBalanceAdjust {
  user_id: number;
  category: LeaveCategory;
  year: number;
  adjustment: string;
  reason?: string;
}