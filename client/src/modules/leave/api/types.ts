/** Type definitions for Employee Leave Management (ELM) module. */

export interface LeaveType {
  id: number;
  code: string;
  name: string;
  max_days_per_year: string;
  requires_substitute: boolean;
  is_continuous_counting: boolean;
  can_carry_forward: boolean;
  is_active: boolean;
  description: string;
}

export interface HolidayCalendar {
  id: number;
  name: string;
  date: string;
  is_restricted: boolean;
  year: number;
  description: string;
}

export interface LeaveBalance {
  id: number;
  employee_id: string;
  leave_type: number;
  leave_type_code: string;
  leave_type_name: string;
  year: number;
  credited: string;
  consumed: string;
  carried_forward: string;
  available: string;
}

export interface LeaveWorkflowHistory {
  id: number;
  actor_id: string;
  action: string;
  from_state: string;
  to_state: string;
  remarks: string;
  created_at: string;
}

export interface LeaveApplication {
  id: number;
  applicant_id: string;
  leave_type: number;
  leave_type_code: string;
  leave_type_name: string;
  start_date: string;
  end_date: string;
  leave_days: string;
  reason: string;
  status: string;
  is_half_day: boolean;
  half_day_period: string;
  station_leave_required: boolean;
  departure_date?: string | null;
  arrival_date?: string | null;
  station_address?: string;
  emergency_contact?: string;
  substitute_id?: string;
  substitute_status: string;
  substitute_remarks?: string;
  substitute_responded_at?: string | null;
  unit_head_id?: string;
  unit_head_recommendation?: string;
  unit_head_remarks?: string;
  unit_head_action_at?: string | null;
  sanctioning_authority_id?: string;
  sanction_remarks?: string;
  sanctioned_at?: string | null;
  cancellation_reason?: string;
  cancellation_requested_at?: string | null;
  resumption_date?: string | null;
  resumption_remarks?: string;
  resumption_status: string;
  resumption_reviewer_id?: string;
  resumption_reviewed_at?: string | null;
  history?: LeaveWorkflowHistory[];
  created_at: string;
  updated_at: string;
}

export interface LeaveApplicationCreatePayload {
  leave_type: number;
  start_date: string;
  end_date: string;
  reason: string;
  is_half_day?: boolean;
  half_day_period?: string;
  substitute_id?: string;
  station_leave_required?: boolean;
  departure_date?: string | null;
  arrival_date?: string | null;
  station_address?: string;
  emergency_contact?: string;
}

export interface LeaveSubstituteResponsePayload {
  response: "accept" | "decline";
  remarks?: string;
}

export interface LeaveReplacementSubstitutePayload {
  substitute_id: string;
  remarks?: string;
}

export interface LeaveReviewActionPayload {
  review_action: "approve" | "reject" | "recommend";
  recommendation?: "RECOMMENDED" | "NOT_RECOMMENDED" | "";
  remarks?: string;
}

export interface LeaveWithdrawPayload {
  remarks?: string;
}

export interface LeaveCancellationRequestPayload {
  reason: string;
}

export interface LeaveCancellationReviewPayload {
  approval_action: "approve" | "reject";
  remarks?: string;
}

export interface LeaveResumptionSubmitPayload {
  resumption_date: string;
  remarks?: string;
}

export interface LeaveResumptionReviewPayload {
  approval_action: "approve" | "reject";
  remarks?: string;
}
