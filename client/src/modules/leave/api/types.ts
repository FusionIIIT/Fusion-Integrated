export interface Page<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export type LeaveCategory = "cl" | "rh" | "scl" | "el" | "col" | "vl";
export type LeaveKind = "new" | "cancellation" | "extension" | "offline";
export type LeaveStatus = 
  | "awaiting_substitute_response"
  | "applicant_action_required"
  | "awaiting_unit_head_review"
  | "awaiting_establishment_routing"
  | "awaiting_final_sanction_decision"
  | "awaiting_director_self_sanction"
  | "approved"
  | "rejected"
  | "withdrawn"
  | "cancelled";

export interface LeaveRequest {
  id: number;
  user_id: number;
  applicant_name?: string;
  kind: LeaveKind;
  source: string;
  category: LeaveCategory;
  status: LeaveStatus;
  start_date: string;
  end_date: string;
  half_day: string;
  purpose: string;
  evidence_note: string;
  station_leave: boolean;
  station_place: string;
  station_reason: string;
  chargeable_days: string;
  year: number;
  base_request: number | null;
  substitute_user_id: number | null;
  substitute_name?: string;
  substitute_status: string;
  unit_head_user_id: number | null;
  unit_head_outcome: string;
  unit_head_note: string;
  establishment_user_id: number | null;
  authority_user_id: number | null;
  is_director_self_sanction: boolean;
  decision: string;
  decided_at: string | null;
  decided_by_user_id: number | null;
  decision_note: string;
  sanction_reference: string;
  task_class: string;
  task_user_id: number | null;
  task_assigned_at: string | null;
  reminder_sent_at: string | null;
  escalated_at: string | null;
  actual_end_date: string | null;
  admin_note: string;
  allowed_actions: string[];
  is_pending: boolean;
  pending_resumption: LeaveResumption | null;
  created_at: string;
  updated_at: string;
}

export interface LeaveResumption {
  id: number;
  request: number;
  actual_date: string;
  details: string;
  status: string;
  approved_end_date: string;
  adjustment_days: string;
  reviewed_by_user_id: number | null;
  reviewed_at: string | null;
  review_note: string;
  created_at: string;
}

export interface LeaveEvent {
  id: number;
  from_status: string;
  to_status: string;
  kind: string;
  actor_user_id: number | null;
  actor_label: string;
  note: string;
  at: string;
}

export interface LeaveBalance {
  id: number;
  user_id: number;
  category: LeaveCategory;
  year: number;
  carried_forward: string;
  credited: string;
  used: string;
  adjusted: string;
  available: number;
}

export interface LeaveNotification {
  id: number;
  kind: string;
  message: string;
  request: number | null;
  read_at: string | null;
  created_at: string;
}

export interface LeavePolicy {
  id: number;
  cl_annual: string;
  rh_annual: string;
  scl_annual: string;
  el_annual_nonfaculty: string;
  el_annual_faculty: string;
  col_annual: string;
  vl_annual_faculty: string;
  vl_to_el_numerator: number;
  vl_to_el_denominator: number;
  el_carry_forward: boolean;
  col_carry_forward: boolean;
  substitute_required_categories: LeaveCategory[];
  scl_evidence_required: boolean;
  col_evidence_required: boolean;
  year_end_month: number;
  year_end_day: number;
  updated_at: string;
}

export interface SubmitLeaveRequest {
  category: LeaveCategory;
  start_date: string;
  end_date: string;
  half_day?: string;
  purpose?: string;
  evidence_note?: string;
  station_leave?: boolean;
  station_place?: string;
  station_reason?: string;
  substitute_user_id?: number | null;
}

export interface ExtensionRequest {
  new_end_date: string;
  reason?: string;
  substitute_user_id?: number | null;
}

export interface CancellationRequest {
  reason?: string;
}

export interface ReviewRequest {
  outcome: "approve" | "reject" | "recommended" | "not_recommended";
  note?: string;
  reference?: string;
}

export interface SanctionRequest {
  outcome: "approve" | "reject";
  note?: string;
  reference?: string;
}

export interface SubstituteResponse {
  response: "accept" | "decline";
}

export interface ResumptionRequest {
  actual_date: string;
  details?: string;
}

export interface ResumptionReviewRequest {
  note?: string;
}

export interface EmployeeSearchResult {
  user_id: number;
  username: string;
  display_name: string;
  kind: string;
  department: string;
}