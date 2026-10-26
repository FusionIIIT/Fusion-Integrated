export type LeaveCategoryCode = "CL" | "RH" | "SCL" | "EL" | "COL" | "VL";

export interface LeaveType {
  id: number;
  code: LeaveCategoryCode | string;
  name: string;
  max_days_per_year: number;
  is_continuous_count: boolean;
  is_faculty_only: boolean;
  is_non_faculty_only: boolean;
  carries_forward: boolean;
  requires_document: boolean;
  is_active: boolean;
}

export interface LeaveBalance {
  id: number;
  leave_type: number;
  leave_type_code: string;
  leave_type_name: string;
  year: number;
  allotted: number;
  used: number;
  credited_from_vl: number;
  available: number;
}

export interface AuditTrailItem {
  id: number;
  actor_id: number;
  action: string;
  from_status: string;
  to_status: string;
  remarks: string;
  created_at: string;
}

export interface LeaveApplication {
  id: number;
  employee_id: number;
  leave_type: number;
  leave_type_code: string;
  leave_type_name: string;
  start_date: string;
  end_date: string;
  is_half_day: boolean;
  half_day_period: "NONE" | "FIRST_HALF" | "SECOND_HALF";
  days: number;
  reason: string;
  status:
    | "DRAFT"
    | "AWAITING_SUBSTITUTE"
    | "APPLICANT_ACTION_REQUIRED"
    | "AWAITING_UNIT_HEAD"
    | "AWAITING_ESTABLISHMENT"
    | "AWAITING_SANCTION"
    | "AWAITING_DIRECTOR_SELF_SANCTION"
    | "APPROVED"
    | "REJECTED"
    | "WITHDRAWN"
    | "CANCELLED";
  is_station_leave: boolean;
  station_destination: string;
  station_start_date: string | null;
  station_end_date: string | null;
  station_address: string;
  station_contact_no: string;
  substitute_id: number | null;
  substitute_status: "NONE" | "PENDING" | "ACCEPTED" | "DECLINED";
  substitute_declined_reason: string;
  substitute_responded_at: string | null;
  unit_head_id: number | null;
  unit_head_recommendation: "NONE" | "RECOMMENDED" | "NOT_RECOMMENDED" | "APPROVED" | "REJECTED";
  unit_head_remarks: string;
  unit_head_decided_at: string | null;
  establishment_id: number | null;
  establishment_remarks: string;
  establishment_routed_at: string | null;
  sanctioning_authority_id: number | null;
  sanctioning_authority_role: string;
  remarks: string;
  decided_at: string | null;
  audit_trail?: AuditTrailItem[];
  created_at: string;
  updated_at: string;
}

export interface HolidayItem {
  id: number;
  year: number;
  date: string;
  name: string;
  is_restricted_holiday: boolean;
  is_closed_holiday: boolean;
  is_published: boolean;
}

export interface ApplyInput {
  leave_type: number;
  start_date: string;
  end_date: string;
  reason: string;
  is_half_day?: boolean;
  half_day_period?: "NONE" | "FIRST_HALF" | "SECOND_HALF";
  is_station_leave?: boolean;
  station_destination?: string;
  station_start_date?: string | null;
  station_end_date?: string | null;
  station_address?: string;
  station_contact_no?: string;
  substitute_id?: number | null;
}
