/** TypeScript types for Employee Leave Management module.
 *  Strictly aligned with serializers.py and openapi/fusion-integrated.v1.yaml.
 */

export interface LeaveTypeSummary {
  code: string;
  name: string;
  is_continuous_count: boolean;
  allows_half_day: boolean;
  requires_substitute: boolean;
  allows_extension: boolean;
  carries_forward: boolean;
}

export interface LeaveType extends LeaveTypeSummary {
  id?: number;
  description?: string;
  requires_medical_certificate?: boolean;
  lapses_at_year_end?: boolean;
  is_active?: boolean;
}

export interface LeaveBalance {
  id: number;
  year: number;
  credited_days: string | number;
  used_days: string | number;
  available_days: string | number;
  leave_type: LeaveTypeSummary;
}

export interface LeaveRequest {
  id: number;
  application_number: string;
  user_id: number;
  cadre: string;
  department: string;
  start_date: string;
  end_date: string;
  is_half_day: boolean;
  half_day_period?: string | null;
  requested_days: string | number;
  reason: string;
  address_during_leave?: string;
  contact_number?: string;
  is_station_leave: boolean;
  station_departure_date?: string | null;
  station_arrival_date?: string | null;
  station_destination?: string;
  status: string;
  current_handler_role?: string | null;
  unit_head_recommendation?: string | null;
  unit_head_remarks?: string | null;
  cancellation_reason?: string | null;
  cancellation_requested_at?: string | null;
  extension_end_date?: string | null;
  extension_days?: string | number | null;
  extension_reason?: string | null;
  actual_days?: string | number | null;
  excess_days?: string | number | null;
  requires_admin_review: boolean;
  reconciliation_status: string;
  is_offline_record: boolean;
  offline_sanction_reference?: string | null;
  offline_sanctioned_by?: string | null;
  offline_sanctioned_date?: string | null;
  created_at: string;
  leave_type: LeaveTypeSummary;
}

export interface SubstituteNomination {
  id: number;
  substitute_user_id: number;
  status: "pending" | "accepted" | "declined" | string;
  remarks: string;
  responded_at?: string | null;
  sequence: number;
  request: LeaveRequest;
}

export interface ResumptionRecord {
  id: number;
  request_id: number;
  expected_date: string;
  actual_resumption_date: string;
  nature: "on_time" | "early" | "late" | string;
  difference_days: string | number;
  remarks: string;
  reviewed_by_user_id?: number | null;
  reviewed_at?: string | null;
  decision?: string | null;
}

export interface DirectoryUser {
  user_id: number;
  username: string;
  display_name: string;
  kind?: string;
  department?: string;
  email?: string;
}

// Request payloads

export interface LeaveApplicationPayload {
  leave_type_code: string;
  start_date: string;
  end_date: string;
  reason: string;
  is_half_day?: boolean;
  half_day_period?: string;
  is_station_leave?: boolean;
  station_departure_date?: string | null;
  station_arrival_date?: string | null;
  station_destination?: string;
  substitute_user_id?: number | null;
  address_during_leave?: string;
  contact_number?: string;
}

export interface SubstituteResponsePayload {
  decision: "accepted" | "declined";
  remarks?: string;
}

export interface LeaveWithdrawPayload {
  remarks?: string;
}

export interface LeaveCancelPayload {
  reason: string;
}

export interface LeaveExtendPayload {
  extension_end_date: string;
  reason: string;
  substitute_user_id?: number | null;
}

export interface LeaveResumePayload {
  actual_resumption_date: string;
  remarks?: string;
}

export interface LeaveReviewPayload {
  decision: "approve" | "reject" | "recommend" | "not_recommend";
  remarks?: string;
}

export interface LeaveSanctionPayload {
  decision: "approve" | "reject";
  remarks?: string;
}

export interface ResumptionReviewPayload {
  decision?: "approved" | "rejected";
  remarks?: string;
}

export interface OfflineLeaveCreatePayload {
  employee_user_id: number;
  leave_type_code: string;
  start_date: string;
  end_date: string;
  reason: string;
  offline_sanction_reference: string;
  offline_sanctioned_by: string;
  offline_sanctioned_date: string;
  is_half_day?: boolean;
  half_day_period?: string;
}
