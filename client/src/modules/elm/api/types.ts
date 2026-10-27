export type LeaveCategory = "CL" | "RH" | "SCL" | "EL" | "COL" | "VL";

export type LeaveRequestStatus =
  | "DRAFT"
  | "PENDING_SUBSTITUTE"
  | "APPLICANT_ACTION_REQUIRED"
  | "PENDING_UNIT_HEAD"
  | "PENDING_ESTABLISHMENT"
  | "PENDING_FINAL_DECISION"
  | "PENDING_DIRECTOR_SANCTION"
  | "APPROVED"
  | "REJECTED"
  | "WITHDRAWN"
  | "CANCELLED";

export interface LeaveWorkflowAction {
  from_status: string;
  to_status: string;
  action: string;
  actor_role: string;
  reason: string;
  at: string;
}

export interface LeaveRequest {
  id: number;
  leave_type: LeaveCategory;
  start_date: string;
  end_date: string;
  purpose: string;
  half_day: "FIRST" | "SECOND" | null;
  chargeable_days: string | null;
  status: LeaveRequestStatus;
  created_at: string;
  submitted_at: string | null;
  workflow_actions: LeaveWorkflowAction[];
}

export interface Page<T> {
  results: T[];
  next: string | null;
  previous: string | null;
}

export interface LeaveRequestInput {
  leave_type: LeaveCategory;
  start_date: string;
  end_date: string;
  purpose: string;
  half_day?: "FIRST" | "SECOND" | null;
  substitute_user_id?: number;
}
