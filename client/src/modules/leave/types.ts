export type LeaveCategory = "CL" | "RH" | "SCL" | "EL" | "COL" | "VL";
export type HalfDayOption = "NONE" | "FIRST_HALF" | "SECOND_HALF";
export type LeaveStatus =
  | "DRAFT"
  | "PENDING_SUBSTITUTE"
  | "SUBSTITUTE_DECLINED"
  | "PENDING_UNIT_HEAD"
  | "PENDING_ESTABLISHMENT"
  | "PENDING_SANCTION"
  | "APPROVED"
  | "REJECTED"
  | "WITHDRAWN"
  | "CANCEL_REQUESTED"
  | "CANCELLED"
  | "EXT_REQUESTED"
  | "RESUMED"
  | "RESUMPTION_REVIEWED";

export interface LeaveBalance {
  id: number;
  user_id: number;
  year: number;
  category: LeaveCategory;
  credited: string | number;
  availed: string | number;
  balance: string | number;
}

export interface LeaveActionLog {
  id: number;
  leave_request_id: number;
  actor_user_id: number;
  action: string;
  from_status: string;
  to_status: string;
  remarks: string;
  created_at: string;
}

export interface LeaveRequest {
  id: number;
  user_id: number;
  category: LeaveCategory;
  start_date: string;
  end_date: string;
  half_day: HalfDayOption;
  computed_days: string | number;
  reason: string;
  status: LeaveStatus;
  substitute_user_id?: number | null;
  substitute_status: string;
  substitute_remarks?: string;
  station_leave: boolean;
  station_address?: string;
  station_contact?: string;
  station_start_date?: string | null;
  station_end_date?: string | null;
  medical_certificate_url?: string;
  unit_head_user_id?: number | null;
  unit_head_recommendation?: string;
  unit_head_remarks?: string;
  sanctioning_authority_user_id?: number | null;
  sanction_remarks?: string;
  offline_entry: boolean;
  offline_reference?: string;
  cancellation_reason?: string;
  extension_base_request_id?: number | null;
  extension_days?: string | number;
  resumption_date?: string | null;
  resumption_remarks?: string;
  resumption_status?: string;
  created_at: string;
  updated_at: string;
  action_logs?: LeaveActionLog[];
}

export interface HolidayCalendar {
  id: number;
  date: string;
  name: string;
  is_restricted: boolean;
  year: number;
  published: boolean;
}

export interface VacationPeriod {
  id: number;
  name: string;
  start_date: string;
  end_date: string;
  year: number;
}
