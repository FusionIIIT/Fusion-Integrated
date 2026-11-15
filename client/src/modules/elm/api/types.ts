export interface LeaveBalance {
  category: string;
  year: number;
  entitlement: string;
  carry_forward: string;
  used: string;
  balance: string;
}

export interface LeavePolicy {
  id: number;
  year: number;
  casual_days: string;
  restricted_holiday_days: string;
  special_casual_days: string;
  earned_days: string;
  commuted_days: string;
  vacation_days: string;
  reminder_after_hours: number;
  escalate_after_hours: number;
  escalation_user_id: number | null;
}

export interface OrgUnit {
  id: number;
  code: string;
  name: string;
  unit_head_user_id: number;
  is_active: boolean;
}

export interface HolidayCalendar {
  id: number;
  year: number;
  name: string;
  status: "draft" | "published" | "superseded";
  published_at: string | null;
  published_by_user_id: number | null;
}

export interface Holiday {
  id: number;
  date: string;
  name: string;
  kind: "closed" | "restricted";
}

export interface VacationPeriod {
  id: number;
  academic_year: string;
  label: string;
  starts_on: string;
  ends_on: string;
  source: string;
}

export interface ApprovalRoute {
  id: number;
  category: string;
  unit_id: number | null;
  designation: string;
  steps: { user_id: number; role: string }[];
  is_active: boolean;
}

export interface LeaveTask {
  id: number;
  sequence: number;
  role: string;
  assigned_user_id: number;
  is_final: boolean;
  status: string;
  assigned_at: string;
  acted_at: string | null;
  decision_note: string;
  request: LeaveRequest;
}

export interface LeaveEvent {
  actor_user_id: number | null;
  event: string;
  from_status: string;
  to_status: string;
  note: string;
  created_at: string;
}

export interface LeaveRequest {
  id: number;
  applicant_user_id: number;
  category: string;
  request_type: "leave" | "cancellation" | "extension" | "resumption";
  status: string;
  starts_on: string;
  ends_on: string;
  half_day_part: string;
  requested_days: string;
  purpose: string;
  station_leave: boolean;
  station_destination: string;
  station_contact: string;
  medical_evidence: string;
  substitute_user_id: number | null;
  substitute_response: string;
  parent_id: number | null;
  actual_resume_date: string | null;
  offline_reference: string;
  submitted_at: string | null;
  decided_at: string | null;
  decision_note: string;
  tasks: LeaveTask[];
  events: LeaveEvent[];
}

export interface Page<T> {
  next: string | null;
  previous: string | null;
  results: T[];
}
