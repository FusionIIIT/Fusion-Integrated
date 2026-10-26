export interface LeavePolicy {
  id: number;
  category: string;
  name: string;
  annual_entitlement: string;
  carry_forward: boolean;
  counting_method: string;
  applies_to: string;
  requires_vacation_period: boolean;
  requires_holiday_calendar: boolean;
  requires_medical_evidence: boolean;
}

export interface LeaveBalance {
  id: number;
  user_id: number;
  category: string;
  year: number;
  entitlement: string;
  balance: string;
  used: string;
  carried_forward: string;
}

export interface HolidayCalendarEntry {
  id: number;
  date: string;
  name: string;
  is_restricted_holiday: boolean;
  year: number;
  published_at: string;
}

export interface ApprovalStep {
  id: number;
  application_id: number;
  step_order: number;
  assigned_user_id: number;
  assigned_role: string;
  step_type: string;
  decision: string;
  comment: string;
  decided_by_user_id?: number | null;
  decided_at?: string | null;
}

export interface LeaveApplication {
  id: number;
  user_id: number;
  category: string;
  status: "submitted" | "recommended" | "not_recommended" | "approved" | "rejected" | "withdrawn" | "cancelled";
  leave_start: string;
  leave_end: string;
  computed_days: string;
  is_half_day: boolean;
  half_day?: string;
  purpose: string;
  station_leave_required: boolean;
  station_leave_city?: string;
  station_leave_purpose?: string;
  substitute_user_id?: number | null;
  substitute_status: "not_requested" | "pending" | "accepted" | "declined";
  substitute_noted_at?: string | null;
  is_extension: boolean;
  extension_of_id?: number | null;
  is_cancellation: boolean;
  cancellation_of_id?: number | null;
  is_resumption: boolean;
  resumption_for_id?: number | null;
  actual_resumption_date?: string | null;
  is_offline_sanctioned: boolean;
  offline_sanction_reference?: string;
  approval_steps: ApprovalStep[];
  created_at: string;
  updated_at: string;
}

export interface ApplyLeavePayload {
  category: string;
  leave_start: string;
  leave_end: string;
  purpose: string;
  is_half_day?: boolean;
  half_day?: string;
  station_leave_required?: boolean;
  station_leave_city?: string;
  station_leave_purpose?: string;
  substitute_user_id?: number | null;
  unit_head_id?: number;
}
