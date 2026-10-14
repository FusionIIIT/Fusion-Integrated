/** Mirrors modules/elm/api/serializers.py. */
export interface Page<T> {
  results: T[];
  next: string | null;
  previous: string | null;
}

export type Category = "CL" | "RH" | "SCL" | "EL" | "COL" | "VL";

export const CATEGORY_LABELS: Record<Category, string> = {
  CL: "Casual Leave",
  RH: "Restricted Holiday",
  SCL: "Special Casual Leave",
  EL: "Earned Leave",
  COL: "Commuted Leave",
  VL: "Vacation Leave",
};

export interface RouteStep {
  step: "unit_head" | "establishment" | "sanction" | "director";
  role: string;
}

export interface LeaveRequest {
  id: number;
  kind: "leave" | "extension" | "offline";
  parent_id: number | null;
  user_id: number;
  applicant_name: string;
  applicant_kind: string;
  applicant_unit: string;
  category: Category;
  category_label: string;
  start_date: string;
  end_date: string;
  half: "" | "first" | "second";
  days: string;
  purpose: string;
  medical_evidence: string;
  station_leave: boolean;
  station_from: string | null;
  station_to: string | null;
  station_address: string;
  substitute_user_id: number | null;
  substitute_name: string;
  substitute_status: string;
  responsibility: string;
  status: string;
  route: RouteStep[];
  stage: number;
  current_role: string;
  recommendation: string;
  decision_note: string;
  decided_at: string | null;
  actual_return_date: string | null;
  resumption_note: string;
  allowed_decisions: string[];
  created_at: string;
  updated_at: string;
}

export interface Transition {
  from_status: string;
  to_status: string;
  event: string;
  actor_role: string;
  note: string;
  at: string;
}

export interface LeaveDetail extends LeaveRequest {
  history: Transition[];
}

export interface LeaveInput {
  category: Category;
  start_date: string;
  end_date: string;
  half: "" | "first" | "second";
  purpose: string;
  medical_evidence: string;
  station_leave: boolean;
  station_from: string | null;
  station_to: string | null;
  station_address: string;
  substitute_user_id: number | null;
  responsibility: string;
}

export interface LedgerEntry {
  id: number;
  category: Category;
  entry_type: string;
  delta: string;
  year: number;
  request_id: number | null;
  note: string;
  at: string;
}

export interface Balance {
  user_id: number;
  display_name?: string;
  balances: Record<Category, string>;
  pending: Record<Category, string>;
  history: LedgerEntry[];
}

export interface Employee {
  user_id: number;
  display_name: string;
  username: string;
  kind: string;
  department: string;
}

export interface PolicyVersion {
  id: number;
  name: string;
  params: Record<string, unknown>;
  hierarchy: Record<string, unknown>;
  effective_from: string;
  status: "draft" | "published";
  published_at: string | null;
  created_at: string;
}

export interface CalendarEntry {
  kind: "closed_holiday" | "restricted_holiday" | "vacation";
  name: string;
  start_date: string;
  end_date: string;
}

export interface CalendarVersion {
  id: number;
  name: string;
  effective_from: string;
  status: "draft" | "published";
  published_at: string | null;
  entries: CalendarEntry[];
  created_at: string;
}

export interface OfflineInput {
  user_id: number;
  category: Category;
  start_date: string;
  end_date: string;
  half: "" | "first" | "second";
  purpose: string;
  sanction_reference: string;
  sanctioned_by: string;
  sanctioned_on: string;
  evidence_note: string;
}

export interface OfflineRecord {
  id: number;
  sanction_reference: string;
  sanctioned_by: string;
  sanctioned_on: string;
  evidence_note: string;
  recorded_by_user_id: number;
  created_at: string;
  leave: LeaveRequest;
}

export interface Notification {
  id: number;
  message: string;
  request_id: number | null;
  created_at: string;
  read_at: string | null;
}
