export interface Page<T> {
  results: T[];
  next: string | null;
  previous: string | null;
}

export interface EmployeeRecord {
  user_id: number;
  employee_category: "faculty" | "staff";
  employment_status: "active" | "retired" | "separated";
  department: string;
  designation: string;
  appointment_type: string;
  appointment_start_date: string | null;
  appointment_end_date: string | null;
  appointment_details: Record<string, unknown>;
  service_history: Record<string, unknown>[];
  retirement_status: string;
  leave_balances: LeaveBalance[];
  created_at: string;
  updated_at: string;
}

export type LeaveType = "casual" | "restricted" | "medical" | "earned" | "vacation" | "sabbatical";

export interface LeaveBalance {
  leave_type: LeaveType;
  available_days: string;
  is_eligible: boolean;
  updated_at: string;
}

export interface LeaveRequest {
  id: number;
  employee_user_id: number;
  leave_type: LeaveType;
  leave_type_display: string;
  duration_days: string;
  justification: string;
  status: "pending_authority" | "pending_next_authority" | "approved" | "rejected";
  current_authority_user_id: number | null;
  authority_step: number;
  created_at: string;
  updated_at: string;
  ledger_entries: { id: number; entry_type: string; amount_delta: string; actor_user_id: number; created_at: string }[];
}

export interface ManagedLeaveBalance extends LeaveBalance {
  id: number;
  employee_user_id: number;
  leave_type_display: string;
}

export interface ClaimIntegrationStatus {
  id: number;
  system: "payroll" | "finance";
  external_status: string;
  external_reference: string;
  details: Record<string, unknown>;
  received_at: string;
  created_at: string;
}

export interface Claim {
  id: number;
  employee_user_id: number;
  employee_category: "faculty" | "staff";
  request_type: "ltc_advance" | "ltc_reimbursement" | "cpda_advance" | "cpda_reimbursement";
  request_type_display: string;
  purpose: string;
  amount: string | null;
  form_data: Record<string, unknown>;
  supporting_documents: { file_id: string; url: string }[];
  status: string;
  status_display: string;
  current_authority_user_id: number | null;
  verification_details: Record<string, unknown>;
  processing_details: Record<string, unknown>;
  processed_at: string | null;
  integration_statuses: ClaimIntegrationStatus[];
  created_at: string;
  updated_at: string;
}

export interface Appraisal {
  id: number;
  employee_user_id: number;
  period: string;
  form_data: Record<string, unknown>;
  status: string;
  status_display: string;
  reviewer_user_ids: number[];
  current_reviewer_index: number;
  current_reviewer_user_id: number | null;
  reviews: { reviewer_user_id: number; action: string; note: string; at: string }[];
  finalized_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkflowRoute {
  id: number;
  employee_category: "faculty" | "staff";
  request_type: Claim["request_type"] | `leave_${LeaveType}`;
  steps: { approver_user_id: number; authority_label: string }[];
  reminder_after_hours: number | null;
  updated_at: string;
}

export interface AppraisalWindow {
  id: number;
  period: string;
  opens_at: string;
  closes_at: string;
  is_active: boolean;
  updated_at: string;
}

export interface AuditEvent {
  id: number;
  entity_type: string;
  entity_id: number;
  actor_user_id: number | null;
  action: string;
  details: Record<string, unknown>;
  created_at: string;
}

export interface HRNotification {
  id: number;
  topic: string;
  subject: string;
  body: string;
  payload: Record<string, unknown>;
  created_at: string;
}
