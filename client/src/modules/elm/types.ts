export type LeaveCategory = "CL" | "RH" | "SCL" | "EL" | "COL" | "VL";

export type LeaveStatus =
  | "awaiting_substitute"
  | "pending_unit_head"
  | "pending_sanction"
  | "approved"
  | "rejected"
  | "withdrawn"
  | "cancelled"
  | "completed";

export interface LeaveBalance {
  user_id: number;
  category: LeaveCategory;
  year: number;
  opening_balance: string;
  credited: string;
  used: string;
  lapsed: string;
  closing_balance: string;
  balance: string;
}

export type LeaveAccount = LeaveBalance;

export interface LeavePolicy {
  category: LeaveCategory;
  annual_entitlement: string;
  faculty_only: boolean;
  continuous_days: boolean;
  carry_forward: boolean;
  allow_half_day: boolean;
  medical_evidence_required: boolean;
  is_active: boolean;
}

export interface CreateLeaveCaseInput {
  case_type: "cancellation" | "extension" | "resumption";
  reason: string;
  requested_start?: string;
  requested_end?: string;
  actual_resumption_date?: string;
  medical_evidence_ref?: string;
  substitute_user_id?: number | null;
}

export interface LeaveSummary {
  employee: {
    user_id: number;
    employee_type: "faculty" | "staff";
    designation: string;
    organization_unit: number | null;
  };
  year: number;
  balances: LeaveBalance[];
  pending_requests: number;
}

export interface LeaveAuditEvent {
  id: number;
  actor_user_id: number;
  action: string;
  note: string;
  created_at: string;
}

export interface LeaveCase {
  id: number;
  leave_request_id: number;
  leave_category: LeaveCategory;
  applicant_user_id: number;
  case_type: "cancellation" | "extension" | "resumption";
  requested_start: string | null;
  requested_end: string | null;
  actual_resumption_date: string | null;
  reason: string;
  status: string;
  workflow_stage: string;
  created_at: string;
  updated_at: string;
}

export interface LeaveRequest {
  id: number;
  applicant_user_id: number;
  category: LeaveCategory;
  start_date: string;
  end_date: string;
  half_day: "none" | "first_half" | "second_half";
  purpose: string;
  station_leave: boolean;
  station_destination: string;
  medical_evidence_ref: string;
  substitute_user_id: number | null;
  substitute_response: "pending" | "accepted" | "declined" | "";
  status: LeaveStatus;
  workflow_stage: string;
  approved_days: string;
  created_at: string;
  updated_at: string;
  cases?: LeaveCase[];
  history?: LeaveAuditEvent[];
  transactions?: {
    id: number;
    category: LeaveCategory;
    amount: string;
    transaction_type: string;
    description: string;
    created_at: string;
  }[];
}

export interface LeaveInbox {
  requests: LeaveRequest[];
  cases: LeaveCase[];
}

export interface LeaveRequestInput {
  category: LeaveCategory;
  start_date: string;
  end_date: string;
  half_day: "none" | "first_half" | "second_half";
  purpose: string;
  station_leave: boolean;
  station_destination: string;
  medical_evidence_ref: string;
  substitute_user_id?: number | null;
}