export type LeaveCategory =
  | "CL"
  | "RH"
  | "EL"
  | "SCL"
  | "COL"
  | "VL"
  | "ML"
  | "PL"
  | "CCL"
  | "SL"
  | "LND"
  | "EOL";

export type LeaveState =
  | "draft"
  | "pending_substitute"
  | "pending_review"
  | "pending_routing"
  | "pending_sanction"
  | "sanctioned"
  | "rejected"
  | "withdrawn"
  | "cancellation_requested"
  | "cancelled"
  | "extension_requested"
  | "active"
  | "resumed"
  | "closed";

export interface LeaveRequest {
  id: number;
  user_id: number;
  category: LeaveCategory;
  starts_on: string;
  ends_on: string;
  half: "none" | "first_half" | "second_half";
  deductible_days: string;
  calendar_days: number;
  reason: string;
  evidence_reference?: string;
  substitute_user_id?: number | null;
  state: LeaveState;
  resumed_on?: string | null;
  created_at: string;
  updated_at: string;
}

export interface LeaveBalance {
  category: string;
  available: string;
  credited: string;
  consumed: string;
  restored: string;
}

export interface LedgerEntry {
  id: number;
  user_id: number;
  year: number;
  category: string;
  days: string;
  reason: string;
  reference_request_id?: number | null;
  note?: string;
  created_at: string;
}

export interface LeaveTransition {
  id: number;
  request_id: number;
  from_state: string;
  to_state: string;
  actor_user_id?: number | null;
  actor_role?: string;
  remark?: string;
  created_at: string;
}

export interface Policy {
  id: number;
  version: string;
  effective_from: string;
  effective_to?: string | null;
  published: boolean;
  note?: string;
  vl_to_el_ratio: string;
  vl_to_el_rounding: string;
  early_return_tail: boolean;
  max_backdate_days: number;
}

export interface Calendar {
  id: number;
  year: number;
  version: string;
  published: boolean;
}

export interface Holiday {
  id: number;
  calendar: number;
  day: string;
  name: string;
  restricted: boolean;
}

export interface VacationPeriod {
  id: number;
  calendar: number;
  name: string;
  starts_on: string;
  ends_on: string;
}
