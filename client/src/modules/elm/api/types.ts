/** Types mirroring the elm serializers, field for field. */
export interface Page<T> {
  results: T[];
  next: string | null;
  previous: string | null;
}

export interface LeaveType {
  id: number;
  code: string;
  name: string;
  annual_entitlement_days: string;
  counts_calendar_days: boolean;
  allows_half_day: boolean;
  requires_reason: boolean;
  effective_from: string;
  is_active: boolean;
}

export interface Holiday {
  id: number;
  date: string;
  name: string;
}

export interface LeaveApplication {
  id: number;
  user_id: number;
  applicant_name: string;
  leave_type: LeaveType;
  start_date: string;
  end_date: string;
  days: string;
  is_half_day: boolean;
  half_day_part: string;
  reason: string;
  status: string;
  decided_by_user_id: number | null;
  decided_at: string | null;
  decision_note: string;
  allowed_transitions: string[];
  created_at: string;
}

export interface LeaveEvent {
  id: number;
  from_status: string;
  to_status: string;
  actor_user_id: number | null;
  actor_name: string;
  note: string;
  at: string;
}

export interface Balance {
  user_id: number;
  leave_type_code: string;
  leave_type_name: string;
  entitled_days: string;
  used_days: string;
  available_days: string;
}

export interface SubmitLeavePayload {
  leave_type_id: number;
  start_date: string;
  end_date: string;
  is_half_day?: boolean;
  half_day_part?: string;
  reason?: string;
}
