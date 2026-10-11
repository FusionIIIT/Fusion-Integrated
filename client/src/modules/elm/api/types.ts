/** Wire shapes for the ELM API (/api/v1/elm/). */

export interface ElmContext {
  user_id: number;
  username: string;
  display_name: string;
  employee_kind: "faculty" | "staff" | null;
  designation_name: string | null;
  unit: { code: string; name: string; unit_type: string } | null;
  is_unit_head: boolean;
}

export interface Balance {
  user_id: number;
  leave_year: string;
  category: string;
  opening_days: string;
  entitled_days: string;
  used_days: string;
  pending_days: string;
  available_days: string;
}

export interface SubstituteNomination {
  id: number;
  nominee_user_id: number;
  status: "pending" | "accepted" | "declined" | "superseded" | "withdrawn";
  responded_at: string | null;
  response_reason: string;
  is_active: boolean;
  created_at: string;
}

export interface LeaveTask {
  id: number;
  request: number | LeaveRequest;
  task_class: string;
  assignee_user_id: number;
  assignee_role: string;
  status: "pending" | "completed" | "cancelled";
  outcome: string;
  reason: string;
  reminder_at: string | null;
  escalation_at: string | null;
  reminded_at: string | null;
  escalated_at: string | null;
  escalation_detail: Record<string, unknown>;
  completed_at: string | null;
  created_at: string;
}

export interface RouteStep {
  role: string;
  decision: string;
  authority?: string | null;
}

export interface LeaveRequest {
  id: number;
  kind: "new" | "cancellation" | "extension";
  category: "CL" | "RH" | "SCL" | "EL" | "COL" | "VL";
  status: string;
  base_request: number | null;
  user_id: number;
  start_date: string | null;
  end_date: string | null;
  start_half: string;
  end_half: string;
  purpose: string;
  days: string;
  leave_year: string;
  station_leave: boolean;
  station_details: Record<string, unknown>;
  evidence: Record<string, unknown>;
  substitute_required: boolean;
  route: RouteStep[];
  current_step: number;
  recommendation: string;
  recommendation_reason: string;
  decided_by_user_id: number | null;
  decided_at: string | null;
  decision_reason: string;
  leave_record: number | null;
  withdrawn_at: string | null;
  withdraw_reason: string;
  tasks?: LeaveTask[];
  substitute_nominations?: SubstituteNomination[];
  created_at: string;
  updated_at: string;
}

export interface TaskWithRequest extends LeaveTask {
  request: LeaveRequest;
}

export interface LeaveRecordItem {
  id: number;
  user_id: number;
  leave_year: string;
  category: string;
  start_date: string;
  end_date: string;
  start_half: string;
  end_half: string;
  days: string;
  status: "ongoing" | "completed" | "cancelled";
  station_leave: boolean;
  actual_end_date: string | null;
  created_at: string;
}

export interface HolidayItem {
  id: number;
  date: string;
  label: string;
  kind: "holiday" | "restricted_holiday";
  closed: boolean;
}

export interface HolidayCalendar {
  id: number;
  name: string;
  year: number;
  published_at: string | null;
  description: string;
  holidays: HolidayItem[];
}

export interface Page<T> {
  results: T[];
  next: string | null;
  previous: string | null;
}

export interface ApplicationPayload {
  category: string;
  start_date: string;
  end_date: string;
  start_half?: string;
  end_half?: string;
  purpose?: string;
  station_leave?: boolean;
  station_details?: Record<string, unknown>;
  evidence?: Record<string, unknown>;
  submit?: boolean;
}
