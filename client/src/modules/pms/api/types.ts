/** Wire types for Patent Management System API.
 *
 *  Corresponds directly with DTO serializers in modules/pms/api/serializers.py.
 */

export interface Page<T> {
  results: T[];
  count?: number;
  next: string | null;
  previous: string | null;
}

export interface Inventor {
  id: number;
  user_id: number;
  name: string;
  email: string;
  department: string;
  is_lead: boolean;
  share_percentage: string;
  consent_status: "pending" | "confirmed" | "declined";
  consent_date: string | null;
}

export interface InventorInput {
  user_id?: number;
  name: string;
  email: string;
  department: string;
  share_percentage: number | string;
  is_lead?: boolean;
}

export interface ApplicationDocument {
  id: number;
  document_type: string;
  title: string;
  version: number;
  file_size: number;
  mime_type: string;
  sensitivity: "public" | "internal" | "confidential";
  uploaded_by_user_id: number;
  is_malware_scanned: boolean;
  created_at: string;
}

export interface DirectorReview {
  id: number;
  application_id: number;
  director_user_id: number;
  decision: "approved" | "rejected" | "revisions_requested";
  justification: string;
  decided_at: string;
  created_at: string;
}

export interface DirectorAssignment {
  id: number;
  application_id: number;
  director_user_id: number;
  assigned_by_user_id: number;
  due_at: string | null;
  status: "pending" | "completed" | "expired";
  created_at: string;
}

export interface PatentBudget {
  id: number;
  application_id: number;
  filing_fees: string;
  attorney_fees: string;
  administrative_costs: string;
  total_cost: string;
  status: "draft" | "submitted" | "approved" | "rejected";
  director_user_id: number | null;
  justification: string;
  reviewed_at: string | null;
  updated_at: string;
}

export interface AttorneyPanel {
  id: number;
  user_id: number;
  name: string;
  firm_name: string;
  email: string;
  specialization: string;
  is_active: boolean;
  max_workload: number;
  current_workload: number;
  created_at: string;
}

export interface AttorneyAssignment {
  id: number;
  application_id: number;
  attorney_user_id: number;
  assigned_by_user_id: number;
  status: "offered" | "accepted" | "declined" | "reassigned";
  responded_at: string | null;
  remarks: string;
  created_at: string;
}

export interface PatentabilityAssessment {
  id: number;
  application_id: number;
  attorney_user_id: number;
  recommendation: "proceed" | "proceed_with_amendments" | "do_not_proceed";
  novelty_analysis: string;
  inventive_step_analysis: string;
  utility_analysis: string;
  prior_art_summary: string;
  opinion_text: string;
  assessed_at: string;
}

export interface PatentLegalAdvice {
  id: number;
  application_id: number;
  attorney_user_id: number;
  topic: string;
  advice_text: string;
  created_at: string;
}

export interface ExternalFilingRecord {
  id: number;
  application_id: number;
  jurisdiction: string;
  filing_number: string;
  filing_date: string;
  patent_office: string;
  confirmation_details: string;
  international_justification: string;
  recorded_by_user_id: number;
  created_at: string;
}

export interface OfficeActionResponse {
  id: number;
  office_action_id: number;
  attorney_user_id: number;
  draft_text: string;
  requires_applicant_approval: boolean;
  applicant_approved: boolean | null;
  applicant_approved_at: string | null;
  submitted_at: string | null;
  submission_details: string;
  created_at: string;
}

export interface ExtensionRequest {
  id: number;
  office_action_id: number;
  attorney_user_id: number;
  requested_days: number;
  reason: string;
  filed_date: string;
  is_granted: boolean | null;
  new_deadline: string | null;
  created_at: string;
}

export interface OfficeAction {
  id: number;
  application_id: number;
  action_number: string;
  action_type: string;
  issue_date: string;
  response_deadline: string;
  description: string;
  status: "pending" | "response_drafted" | "applicant_approved" | "submitted" | "resolved";
  recorded_by_user_id: number;
  created_at: string;
  responses: OfficeActionResponse[];
  extension_requests: ExtensionRequest[];
}

export interface MaintenanceSchedule {
  id: number;
  post_grant_id: number;
  cycle_year: number;
  due_date: string;
  fee_amount: string;
  status: "scheduled" | "decision_requested" | "renewal_approved" | "renewed" | "do_not_renew";
  payment_record_reference: string;
  completed_at: string | null;
  created_at: string;
}

export interface RenewalDecision {
  id: number;
  schedule_id: number;
  director_user_id: number;
  decision: "renew" | "do_not_renew";
  justification: string;
  created_at: string;
}

export interface PostGrantPatent {
  id: number;
  application_id: number;
  patent_number: string;
  grant_date: string;
  term_years: number;
  expiry_date: string;
  current_cycle: number;
  created_at: string;
  schedules?: MaintenanceSchedule[];
}

export interface LicensingRequest {
  id: number;
  application_id: number;
  licensee_name: string;
  licensee_contact: string;
  license_type: "exclusive" | "non_exclusive" | "sole";
  proposed_terms: string;
  royalty_rate: string;
  financial_terms: string;
  status: "draft" | "submitted" | "under_review" | "approved" | "executed" | "rejected";
  requested_by_user_id: number;
  reviewed_by_user_id: number | null;
  review_notes: string;
  created_at: string;
  updated_at: string;
}

export interface PatentAppeal {
  id: number;
  application_id: number;
  applicant_user_id: number;
  grounds: string;
  justification: string;
  status: "draft" | "filed" | "hearing_scheduled" | "allowed" | "dismissed";
  filed_at: string;
  resolved_at: string | null;
}

export interface PriorArtAttachment {
  id: number;
  search_record_id: number;
  application_id: number;
  relevance_notes: string;
  attached_at: string;
}

export interface PriorArtSearchRecord {
  id: number;
  application_id: number | null;
  user_id: number;
  query_string: string;
  databases_searched: string[];
  results_count: number;
  session_notes: string;
  created_at: string;
}

export interface PatentAuditLog {
  id: number;
  application_id: number;
  user_id: number;
  actor_role: string;
  action_type: string;
  previous_state: string;
  new_state: string;
  details: Record<string, unknown>;
  ip_address: string;
  created_at: string;
}

export interface PatentApplicationListItem {
  id: number;
  application_no: string;
  title: string;
  domain: string;
  status: string;
  user_id: number;
  primary_inventor_name: string;
  has_budget: boolean;
  budget_status: string;
  submitted_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PatentApplicationDetail {
  id: number;
  application_no: string;
  title: string;
  abstract: string;
  description: string;
  claims: string;
  domain: string;
  filing_type: string;
  status: string;
  user_id: number;
  is_confidential: boolean;
  submitted_at: string | null;
  revision_deadline: string | null;
  created_at: string;
  updated_at: string;
  inventors: Inventor[];
  documents: ApplicationDocument[];
  reviews: DirectorReview[];
  budget: PatentBudget | null;
  filing_record: ExternalFilingRecord | null;
  office_actions: OfficeAction[];
  post_grant: PostGrantPatent | null;
  appeals: PatentAppeal[];
}

export interface PortfolioAnalytics {
  total_applications: number;
  active_patents: number;
  granted_patents: number;
  by_status: Record<string, number>;
  by_domain: Record<string, number>;
  filing_trends: { year: number; count: number }[];
  budget_summary: {
    total_allocated: string;
    filing_fees_total: string;
    attorney_fees_total: string;
  };
}
