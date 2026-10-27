export type LeaveCategory = "CL" | "RH" | "SCL" | "EL" | "VL" | "COL";

export type LeaveStatus =
  | "DRAFT"
  | "AWAITING_SUBSTITUTE_RESPONSE"
  | "AWAITING_APPLICANT_ACTION"
  | "AWAITING_UNIT_HEAD_REVIEW"
  | "AWAITING_ESTABLISHMENT_REVIEW"
  | "AWAITING_SANCTION_AUTHORITY_REVIEW"
  | "APPROVED"
  | "REJECTED"
  | "WITHDRAWN"
  | "AWAITING_CANCELLATION_REVIEW"
  | "CANCELLED"
  | "AWAITING_EXTENSION_REVIEW"
  | "AWAITING_RESUMPTION_REVIEW";

export interface SubstituteAssignment {
  id: number;
  substitute_id: number;
  status: "PENDING" | "ACCEPTED" | "DECLINED";
  remarks: string;
  responded_at?: string;
}

export interface LeaveRequest {
  id: number;
  applicant_id: number;
  category: LeaveCategory;
  start_date: string;
  end_date: string;
  duration_days: string;
  is_half_day: boolean;
  half_day_type?: "first_half" | "second_half";
  reason: string;
  is_station_leave: boolean;
  station_address?: string;
  emergency_contact?: string;
  status: LeaveStatus;
  unit_head_recommendation?: string;
  unit_head_remarks?: string;
  sanctioning_authority_remarks?: string;
  substitute_assignments?: SubstituteAssignment[];
  created_at: string;
  updated_at: string;
}

export interface LeaveAccount {
  id: number;
  category: LeaveCategory;
  year: number;
  allotted: string;
  used: string;
  pending: string;
  available: string;
}
