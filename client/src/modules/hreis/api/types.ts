/** Wire DTOs; server owns scope, revisions, and state transitions. */
export interface Page<T> {
  count?: number;
  results: T[];
  next: string | null;
  previous: string | null;
}

export interface ServiceRecord {
  id: number;
  user_id: number;
  appointment_details: Record<string, unknown>;
  department: string;
  designation_snapshot: string;
  service_history: unknown[];
  leave_balances: Record<string, string>;
  retirement_status: string;
  revision: number;
  created_at: string;
  updated_at: string;
}

export interface RecordFields {
  appointment_details: Record<string, unknown>;
  department: string;
  designation_snapshot: string;
  service_history: unknown[];
  retirement_status: string;
}

export interface CreateRecord extends RecordFields {
  user_id: number;
}

export interface UpdateRecord {
  id: number;
  expected_revision: number;
  fields: Partial<RecordFields>;
}

export interface HRRequest {
  id: number;
  user_id: number;
  family: "leave" | "appraisal" | "ltc" | "cpda";
  subtype: string;
  state: string;
  payload: Record<string, unknown>;
  claim_summary: {
    purpose: string;
    amount: string | null;
    prescribed_form_reference: string;
    hr_verified: boolean;
    financial_verified: boolean;
    payment_status: string | null;
    status_history?: Array<{
      source_system: string;
      external_status_reference: string;
      payment_status: string;
      recorded_at: string;
    }>;
  } | null;
  appraisal_summary: {
    period_key: string;
    submitted_form: Record<string, unknown>;
    reviewer_user_ids: number[];
  } | null;
  route_step: number;
  route_total_steps: number;
  submitted_at: string | null;
  created_at: string;
  updated_at: string;
}


export interface HRRequestDetail extends HRRequest {
  history: Array<{
    source: string;
    event: string;
    target: string;
    acting_designation: string;
    reason: string;
    recorded_at: string;
  }>;
}

export interface HRPolicy {
  id: number;
  family: "leave" | "appraisal" | "ltc" | "cpda";
  version: number;
  effective_from: string;
  effective_until: string | null;
  parameters: Record<string, unknown>;
  approved_by_user_id: number;
  approved_designation: string;
  recorded_at: string;
}

export interface HRPolicyInput {
  family: HRPolicy["family"];
  version: number;
  effective_from: string;
  effective_until: string | null;
  parameters: Record<string, unknown>;
}

export interface LeaveInput {
  leave_type: string;
  duration: string;
  justification: string;
}

export interface VerifiedLeaveCreditInput {
  user_id: number;
  leave_type: string;
  quantity: string;
  evidence_reference: string;
}

export interface VerifiedLeaveCreditRecord {
  id: number;
  user_id: number;
  leave_type: string;
  quantity: string;
  recorded_at: string;
}

export interface ClaimInput {
  family: "ltc" | "cpda";
  subtype: "advance" | "reimbursement";
  prescribed_form_reference?: string;
  purpose?: string;
  amount?: string;
  document_references?: string[];
}

export interface AppraisalInput {
  period_key: string;
  submitted_form: Record<string, unknown>;
}

export interface ClaimReviewInput {
  id: number;
  document_review_reference: string;
  eligibility_basis: string;
}

export interface FinancialReviewInput {
  id: number;
  financial_review_reference: string;
}

export interface FinancialReviewRecord {
  request_id: number;
  financial_review_reference: string;
  reviewed_by_user_id: number;
}

export interface FinancialProcessingInput {
  id: number;
  financial_review_reference: string;
  source_system: "finance" | "payroll";
  external_status_reference: string;
  payment_status: "processing" | "payment_pending" | "paid" | "failed";
}

export interface RequestDecisionInput {
  id: number;
  event: "approve" | "reject" | "forward";
  reason: string;
}

export interface AssignReviewersInput {
  id: number;
  reviewer_user_ids: number[];
}

export interface AppraisalDecisionInput {
  id: number;
  event: "forward" | "finalize";
}

export interface HRComplianceRequestStatus {
  id: number;
  user_id: number;
  family: string;
  state: string;
  created_at: string;
  submitted_at: string | null;
}

export interface HRAudit {
  id: number;
  actor_user_id: number | null;
  acting_designation: string;
  subject_user_id: number | null;
  action: string;
  resource_kind: string;
  resource_id: number;
  data: { changed_fields?: string[]; revision?: number };
  recorded_at: string;
}

export interface HRNotification {
  id: number;
  title: string;
  message: string;
  request_id: number | null;
  created_at: string;
  read_at: string | null;
}
