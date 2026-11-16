export type LeaveType =
  | "casual"
  | "restricted"
  | "medical"
  | "earned"
  | "vacation"
  | "sabbatical";

export type LeaveStatus =
  | "draft"
  | "pending_current_authority"
  | "approved"
  | "rejected"
  | "cancelled";

export type ApprovalOutcome = "approved" | "rejected" | "forwarded";

export interface ApprovalDecision {
  id: number;
  request_id: number;
  authority_id: number;
  outcome: ApprovalOutcome;
  remarks: string;
  next_authority_id?: number | null;
  decided_at: string;
}

export interface LeaveRequest {
  id: number;
  user_id: number;
  leave_type: LeaveType;
  start_date: string;
  end_date: string;
  duration_days: number;
  justification: string;
  status: LeaveStatus;
  current_authority_id: number | null;
  current_authority_role: string;
  forward_count: number;
  cancellation_reason?: string;
  submission_date: string;
  decisions: ApprovalDecision[];
  created_at: string;
  updated_at: string;
}

export interface LeaveBalance {
  id: number;
  user_id: number;
  leave_type: LeaveType;
  year: number;
  total_entitlement: number;
  consumed_days: number;
  available_balance: number;
  created_at: string;
  updated_at: string;
}

export interface SubmitLeaveInput {
  leave_type: LeaveType;
  start_date: string;
  end_date: string;
  duration_days: number;
  justification: string;
}

export interface DecideLeaveInput {
  outcome: "approved" | "rejected" | "forwarded";
  remarks?: string;
  next_authority_id?: number;
}

export interface CancelLeaveInput {
  reason?: string;
}
