/** Wire types derived from OpenAPI; run python docs/09-hreis/scripts/hreis_client_types.py. */

export interface AppraisalDecision {
  event: AppraisalDecisionEventEnum;
}

export type AppraisalDecisionEventEnum = "forward" | "finalize";

export interface AppraisalSubmit {
  period_key: string;
  submitted_form: Record<string, unknown>;
}

export interface AppraisalSummary {
  period_key: string;
  submitted_form: Record<string, unknown>;
  reviewer_user_ids: Array<number>;
}

export interface AuditRead {
  id: number;
  actor_user_id: (number) | null;
  acting_designation: string;
  subject_user_id: (number) | null;
  action: string;
  resource_kind: string;
  resource_id: number;
  data: Record<string, unknown>;
  recorded_at: string;
}

export interface ClaimReview {
  document_review_reference: string;
  eligibility_basis: string;
}

export interface ClaimSubmit {
  family: ClaimSubmitFamilyEnum;
  subtype: SubtypeEnum;
  prescribed_form_reference?: string;
  purpose?: string;
  amount?: string;
  document_references?: Array<string>;
}

export type ClaimSubmitFamilyEnum = "ltc" | "cpda";

export interface ClaimSummary {
  purpose: string;
  amount: (string) | null;
  prescribed_form_reference: string;
  hr_verified: boolean;
  financial_verified: boolean;
  payment_status: (string) | null;
  status_history: Array<FinancialStatusRead>;
}

export interface ComplianceRequest {
  id: number;
  user_id: number;
  family: string;
  state: string;
  created_at: string;
  submitted_at: (string) | null;
}

export interface Decision {
  event: DecisionEventEnum;
  reason?: string;
}

export type DecisionEventEnum = "approve" | "reject" | "forward";

export interface FinancialProcessing {
  financial_review_reference: string;
  source_system?: (SourceSystemEnum | NullEnum) | null;
  external_status_reference?: (string) | null;
  payment_status?: (PaymentStatusEnum | NullEnum) | null;
}

export interface FinancialReview {
  financial_review_reference: string;
}

export interface FinancialReviewRead {
  request_id: number;
  financial_review_reference: string;
  reviewed_by_user_id: number;
}

export interface FinancialStatusRead {
  source_system: (string) | null;
  external_status_reference: (string) | null;
  payment_status: (string) | null;
  recorded_at: string;
}

export interface LeaveSubmit {
  leave_type: LeaveTypeEnum;
  duration: string;
  justification: string;
}

export type LeaveTypeEnum = "Casual" | "Restricted" | "Medical" | "Earned" | "Vacation" | "Sabbatical";

export interface MyLeaveBalances {
  user_id: number;
  leave_balances: Record<string, string>;
}

export interface NotificationRead {
  id: number;
  title: string;
  message: string;
  request_id: (number) | null;
  created_at: string;
  read_at: (string) | null;
}

export type NullEnum = null;

export type PaymentStatusEnum = "processing" | "payment_pending" | "paid" | "failed";

export interface PolicyCreate {
  family: PolicyCreateFamilyEnum;
  version: number;
  effective_from: string;
  effective_until?: (string) | null;
  parameters: Record<string, unknown>;
}

export type PolicyCreateFamilyEnum = "leave" | "appraisal" | "ltc" | "cpda";

export interface PolicyRead {
  id: number;
  family: string;
  version: number;
  effective_from: string;
  effective_until: (string) | null;
  parameters: Record<string, unknown>;
  approved_by_user_id: number;
  approved_designation: string;
  recorded_at: string;
}

export interface RecordCreate {
  user_id: number;
  appointment_details: Record<string, unknown>;
  department: string;
  designation_snapshot: string;
  service_history: Array<unknown>;
  retirement_status?: string;
}

export interface RecordRead {
  id: number;
  user_id: number;
  appointment_details: Record<string, unknown>;
  department: string;
  designation_snapshot: string;
  service_history: Array<unknown>;
  leave_balances: Record<string, string>;
  retirement_status: string;
  revision: number;
  created_at: string;
  updated_at: string;
}

export interface RequestDetailRead {
  id: number;
  user_id: number;
  family: string;
  subtype: string;
  state: string;
  payload: Record<string, unknown>;
  claim_summary: (ClaimSummary) | null;
  appraisal_summary: (AppraisalSummary) | null;
  route_step: number;
  route_total_steps: number;
  submitted_at: (string) | null;
  created_at: string;
  updated_at: string;
  history: Array<RequestTransitionRead>;
}

export interface RequestRead {
  id: number;
  user_id: number;
  family: RequestReadFamilyEnum;
  subtype: string;
  state: string;
  payload: Record<string, unknown>;
  claim_summary: (ClaimSummary) | null;
  appraisal_summary: (AppraisalSummary) | null;
  route_step: number;
  route_total_steps: number;
  submitted_at: (string) | null;
  created_at: string;
  updated_at: string;
}

export type RequestReadFamilyEnum = "leave" | "appraisal" | "ltc" | "cpda";

export interface RequestTransitionRead {
  source: string;
  event: string;
  target: string;
  acting_designation: string;
  reason: string;
  recorded_at: string;
}

export interface ReviewerAssignment {
  reviewer_user_ids: Array<number>;
}

export type SourceSystemEnum = "payroll" | "finance";

export type SubtypeEnum = "advance" | "reimbursement";

export interface VerifiedLeaveCredit {
  user_id: number;
  leave_type: LeaveTypeEnum;
  quantity: string;
  evidence_reference: string;
}

export interface VerifiedLeaveCreditRead {
  id: number;
  user_id: number;
  leave_type: string;
  quantity: string;
  recorded_at: string;
}

export interface Page<T> {
  next?: (string) | null;
  previous?: (string) | null;
  results: T[];
}

export type ServiceRecord = RecordRead;
export type CreateRecord = RecordCreate;
export type HRRequest = RequestRead;
export type HRRequestDetail = RequestDetailRead;
export type HRPolicy = PolicyRead;
export type HRPolicyInput = PolicyCreate;
export type LeaveInput = LeaveSubmit;
export type ClaimInput = ClaimSubmit;
export type AppraisalInput = AppraisalSubmit;
export type VerifiedLeaveCreditInput = VerifiedLeaveCredit;
export type VerifiedLeaveCreditRecord = VerifiedLeaveCreditRead;
export type FinancialReviewRecord = FinancialReviewRead;
export type HRAudit = AuditRead;
export type HRNotification = NotificationRead;
export type HRComplianceRequestStatus = ComplianceRequest;
export type LeaveBalances = MyLeaveBalances;
export type ClaimReviewInput = ClaimReview & { id: number };
export type FinancialReviewInput = FinancialReview & { id: number };
export type FinancialProcessingInput = FinancialProcessing & { id: number };
export type RequestDecisionInput = Decision & { id: number };
export type AssignReviewersInput = ReviewerAssignment & { id: number };
export type AppraisalDecisionInput = AppraisalDecision & { id: number };

export interface RecordFields {
  appointment_details: Record<string, unknown>;
  department: string;
  designation_snapshot: string;
  service_history: unknown[];
  retirement_status: string;
}

export interface UpdateRecord {
  id: number;
  expected_revision: number;
  fields: Partial<RecordFields>;
}
