/** Wire types for the Employee Leave Management (ELM) API. */

export interface LeaveType {
  id: number;
  code: string;
  name: string;
  description: string;
}

export type LeaveStatus =
  | "DRAFT"
  | "AWAITING_SUBSTITUTE_RESPONSE"
  | "APPLICANT_ACTION_REQUIRED"
  | "PENDING_UNIT_HEAD"
  | "PENDING_ESTABLISHMENT"
  | "PENDING_FINAL_SANCTION"
  | "AWAITING_DIRECTOR_SELF_SANCTION"
  | "CANCELLATION_PENDING_UNIT_HEAD"
  | "CANCELLATION_PENDING_ESTABLISHMENT"
  | "CANCELLATION_PENDING_FINAL_DECISION"
  | "APPROVED"
  | "REJECTED"
  | "WITHDRAWN"
  | "CANCELLED";

export interface LeaveRequest {
  id: number;
  employee_user_id: number;
  leave_type__code: string;
  start_date: string;
  end_date: string;
  half_day_type: "FULL" | "FIRST_HALF" | "SECOND_HALF";
  reason: string;
  status: LeaveStatus;
  is_station_leave: boolean;
  created_at: string;
}

export interface LeaveBalance {
  leave_type__code: string;
  year: number;
  credited: string;
  used: string;
}

export interface SubstituteResponse {
  id: number;
  leave_request_id: number;
  status: "PENDING" | "ACCEPTED" | "DECLINED";
  remarks: string;
  responded_at: string | null;
}
