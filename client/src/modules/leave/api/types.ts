/** Shapes the leave endpoints return. Kept narrow on purpose: a field the UI
 *  does not render is a field the server is free to change. */

export type Category = "CL" | "RH" | "SCL" | "EL" | "COL" | "VL";
export type Half = "FIRST" | "SECOND";

export interface LeaveRequest {
  id: number;
  user_id: number;
  category: Category;
  state: string;
  starts_on: string;
  ends_on: string;
  half: string;
  reason: string;
  requested_days: string;
  actual_days: string | null;
  station_leave: boolean;
  station_destination: string;
  resumed_on: string | null;
  decided_at: string | null;
  created_at: string;
}

export interface Transition {
  id: number;
  from_state: string;
  to_state: string;
  event: string;
  actor_role: string;
  actor_user_id: number | null;
  remark: string;
  workflow_ref: string;
  created_at: string;
}

export interface Balance {
  category: Category;
  available: string;
  credited: string;
  consumed: string;
  restored: string;
}

export interface LedgerEntry {
  id: number;
  year: number;
  category: Category;
  days: string;
  reason: string;
  request_id: number | null;
  note: string;
  created_at: string;
}

export interface ApplyPayload {
  category: Category;
  starts_on: string;
  ends_on: string;
  reason: string;
  half?: Half | null;
  substitute_user_id?: number | null;
  station?: { destination: string; from: string; to: string } | null;
}

export interface Policy {
  id: number;
  version: string;
  effective_from: string;
  effective_to: string | null;
  published: boolean;
  note: string;
  vl_to_el_ratio: string;
  vl_to_el_rounding: string;
  early_return_tail: string;
}

export interface CategoryRule {
  id: number;
  category: Category;
  annual_credit: string;
  carries_forward: boolean;
  carry_forward_cap: string | null;
  applies_to_faculty: boolean | null;
  requires_evidence: boolean;
}

export interface Calendar {
  id: number;
  year: number;
  version: string;
  published: boolean;
}

export interface Holiday {
  id: number;
  day: string;
  name: string;
  restricted: boolean;
}

export interface VacationPeriod {
  id: number;
  name: string;
  starts_on: string;
  ends_on: string;
}
