export type PatentApplicationStatus =
  | "draft" | "submitted" | "under_review" | "approved" | "needs_revision"
  | "resubmitted" | "rejected" | "expired" | "appeal_submitted"
  | "rejection_upheld" | "remanded_for_amendment" | "decision_modified"
  | "filed" | "office_action_recorded" | "awaiting_applicant_approval"
  | "applicant_approved" | "response_ready" | "response_submitted"
  | "granted" | "renewal_decision_requested" | "renewal_approved"
  | "do_not_renew" | "renewed" | "withdrawn";

export interface CoInventor {
  id: number;
  user_id: number | null;
  name: string;
  email: string;
  department: string;
  ownership_percentage: string;
  consent_given: boolean;
  agreement_signed: boolean;
  withdrawal_consent_given: boolean;
}

export interface ApplicationDocument {
  id: number;
  doc_type: string;
  title: string;
  file_format: string;
  file_size_bytes: number;
  sensitivity: string;
  version: number;
  is_current: boolean;
  uploaded_by_user_id: number;
  file_url: string;
  created_at: string;
}

export interface PatentBudget {
  id: number;
  filing_fees: string;
  attorney_fees: string;
  administrative_costs: string;
  total_cost: string;
  status: string;
  threshold_limit: string;
  decided_by_user_id: number | null;
  decided_at: string | null;
  justification: string;
}

export interface AttorneyAssignment {
  id: number;
  attorney_user_id: number;
  assigned_by_user_id: number;
  status: "offered" | "accepted" | "declined";
  decline_reason: string;
  decided_at: string | null;
  is_active: boolean;
  created_at: string;
}

export interface OfficeAction {
  id: number;
  action_type: string;
  issue_date: string;
  due_date: string;
  details: string;
  status: string;
  requires_applicant_review: boolean;
  draft_response: string;
  applicant_approved: boolean;
  extension_months: number;
  response_submitted_date: string | null;
  submission_details: string;
  created_at: string;
}

export interface MaintenanceRecord {
  id: number;
  cycle_number: number;
  fee_due_date: string;
  fee_amount: string;
  decision_requested: boolean;
  director_decision: string;
  renewal_decided_at: string | null;
  maintenance_status: string;
  action_recorded_date: string | null;
  transaction_reference: string;
}

export interface PatentApplication {
  id: number;
  application_no: string;
  title: string;
  abstract: string;
  detailed_description: string;
  claims: string;
  domain: string;
  status: PatentApplicationStatus;
  applicant_user_id: number;
  assigned_director_user_id: number | null;
  assigned_attorney_user_id: number | null;
  director_assigned_at: string | null;
  review_deadline: string | null;
  revision_deadline: string | null;
  jurisdiction: string;
  is_international: boolean;
  international_justification: string;
  external_filing_id: string;
  external_filing_date: string | null;
  filing_confirmation: string;
  format_validated: boolean;
  grant_date: string | null;
  patent_number: string;
  is_withdrawn: boolean;
  withdrawal_reason: string;
  withdrawal_date: string | null;
  created_at: string;
  updated_at: string;
  coinventors: CoInventor[];
  documents: ApplicationDocument[];
  budget: PatentBudget | null;
  director_reviews: Array<{
    id: number; decision: string; justification: string; feedback: string;
    director_user_id: number; decided_at: string;
  }>;
  attorney_assignments: AttorneyAssignment[];
  office_actions: OfficeAction[];
  maintenance_records: MaintenanceRecord[];
}

export interface PatentAppeal {
  id: number;
  applicant_user_id: number;
  grounds: string;
  justification: string;
  status: string;
  outcome: string;
  director_user_id: number | null;
  outcome_justification: string;
  decided_at: string | null;
  created_at: string;
}

export interface LicensingRequest {
  id: number;
  requested_by_user_id: number;
  licensee_name: string;
  request_type: string;
  commercial_terms: string;
  status: string;
  negotiation_notes: string;
  agreement_reference: string;
  is_confidential: boolean;
  created_at: string;
}

export interface AttorneyPanelEntry {
  id: number;
  attorney_user_id: number;
  name: string;
  firm_name: string;
  email: string;
  is_approved: boolean;
  expertise_domains: string[];
  current_workload: number;
  max_workload: number;
}

export interface PmsConfiguration {
  key: string;
  value: unknown;
  description: string;
}

export interface PmsReport {
  total_applications: number;
  status_distribution: Record<string, number>;
  domain_distribution: Record<string, number>;
}

export interface WorkflowOversight {
  application_id: number;
  application_no: string;
  domain: string;
  status: string;
  assigned_director_user_id: number | null;
  assigned_attorney_user_id: number | null;
  review_deadline: string | null;
  revision_deadline: string | null;
  budget_status: string | null;
  attorney_assignment_statuses: string[];
  office_actions: Array<{
    id: number; due_date: string; status: string;
    requires_applicant_review: boolean; applicant_approved: boolean;
  }>;
  maintenance: Array<{
    id: number; cycle_number: number; fee_due_date: string;
    maintenance_status: string; director_decision: string;
  }>;
}

export interface PmsAuditEntry {
  id: number;
  application_id: number | null;
  actor_user_id: number | null;
  action_type: string;
  from_state: string;
  to_state: string;
  details: Record<string, unknown>;
  timestamp: string;
}
