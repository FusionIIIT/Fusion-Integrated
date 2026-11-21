/** Mirrors modules/leave/api/serializers.py. */
export type Category = "CL" | "RH" | "SCL" | "EL" | "COL" | "VL";
export type Half = "full" | "first" | "second";

export interface Page<T> { next: string | null; previous: string | null; results: T[] }

export interface Transition {
  from_status: string; to_status: string; event: string;
  actor_user_id: number | null; note: string; at: string;
}

export interface LeaveRequest {
  id: number; user_id: number; applicant_name: string;
  kind: "new" | "cancellation" | "extension"; parent: number | null;
  category: Category; start_date: string; end_date: string; half: Half; days: string;
  purpose: string; station_leave: boolean; station_address: string;
  medical_evidence_ref: string; status: string;
  substitute_user_id: number | null; unit_head_user_id: number | null;
  establishment_user_id: number | null; sanctioning_user_id: number | null;
  unit_head_final: boolean; director_self: boolean; recommendation: string;
  source: "online" | "offline"; offline_reference: string;
  created_at: string; decided_at: string | null; resumption_status: string;
  transitions?: Transition[];
}

export interface Balance {
  category: Category; label: string; balance: string; held: string; available: string;
}

export interface Resumption {
  id: number; leave: LeaveRequest; actual_date: string; remarks: string;
  status: string; outcome: string; adjustment_days: string | null;
}

export interface Employee {
  user_id: number; display_name: string; kind: string; department: string;
}

export interface Policy {
  category: Category; annual_days: string; requires_substitute: boolean;
  max_days_per_request: string | null;
}

export interface Unit { id: number; name: string; head_user_id: number | null; parent_name: string }

export interface AuthorityRule {
  id: number; category: Category; unit_name: string; applicant_kind: string;
  sanctioning_user_id: number; establishment_user_id: number | null;
}

export interface Holiday { date: string; name: string; kind: "closed" | "restricted" }

export interface HolidayCalendar {
  id: number; year: number; title: string; status: string;
  published_at: string | null; holidays: Holiday[];
}

export interface ApplyInput {
  category: Category; start_date: string; end_date: string; half: Half; purpose: string;
  substitute_user_id?: number | null; station_leave: boolean; station_address: string;
  medical_evidence_ref: string;
}
