/** Wire types for ELM, mirroring modules/leave/api/serializers.py. */
export type LeaveType = "CL" | "RH" | "SCL" | "EL" | "COL" | "VL";

export interface Page<T> {
  count: number;
  results: T[];
}

export interface LeaveBalance {
  id: number;
  year: string;
  leave_type: LeaveType;
  entitled: string;
  carried_forward: string;
  availed: string;
  available: string;
}

export interface LeaveApproval {
  step_role: string;
  action: string;
  actor_user_id: number | null;
  note: string;
  at: string;
}

export interface LeaveApplication {
  id: number;
  user_id: number;
  kind: "leave" | "extension" | "cancellation";
  leave_type: LeaveType;
  start_date: string;
  end_date: string;
  half_day: "" | "first" | "second";
  days: string;
  reason: string;
  station_leave: boolean;
  station_place: string;
  substitute_user_id: number | null;
  substitute_status: string;
  status: string;
  pending_role: string;
  unit_head_recommendation: string;
  authority_chain: string[];
  actual_end_date: string | null;
  decision_note: string;
  decided_at: string | null;
  created_at: string;
  approvals: LeaveApproval[];
}

export interface Holiday {
  id: number;
  year: string;
  on_date: string;
  name: string;
  is_closed_holiday: boolean;
  is_published: boolean;
}

export interface ApplyPayload {
  leave_type: LeaveType;
  start_date: string;
  end_date: string;
  half_day?: string;
  reason?: string;
  station_leave?: boolean;
  station_place?: string;
  substitute_user_id?: number | null;
}
