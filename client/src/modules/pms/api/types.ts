// Wire shapes of the PMS API, field for field as modules/pms/api/serializers.py returns them.

export interface Page<T> {
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface ApplicationRow {
  id: number;
  reference: string;
  title: string;
  status: string;
  domain_code: string;
  applicant_user_id: number;
  applicant_name: string;
  submitted_at: string | null;
  updated_at: string;
  revision_due_on: string | null;
  appeal_due_on: string | null;
}

export interface Inventor {
  id: number;
  user_id: number | null;
  name: string;
  email: string;
  affiliation: string;
  share_percent: string;
  agreement_completed_at: string | null;
  agreement_reference: string;
  consent_recorded_at: string | null;
}

export interface ReviewCycle {
  id: number;
  cycle_no: number;
  director_user_id: number;
  director_name: string;
  assigned_on: string;
  due_on: string;
  status: string;
  decision: string;
  justification: string;
  decided_at: string | null;
}

export interface Appeal {
  id: number;
  application_id: number;
  director_user_id: number | null;
  director_name: string;
  grounds: string;
  justification: string;
  status: string;
  outcome: string;
  modified_decision: string;
  outcome_note: string;
  created_at: string;
  decided_at: string | null;
}

export interface Assignment {
  id: number;
  application_id: number;
  application_reference: string;
  application_title: string;
  attorney_user_id: number;
  attorney_name: string;
  is_exception: boolean;
  exception_reason: string;
  status: string;
  responded_at: string | null;
  decline_reason: string;
  created_at: string;
}

export interface Budget {
  id: number;
  application_id: number;
  filing_fee: string;
  attorney_fee: string;
  admin_cost: string;
  total: string;
  status: string;
  decision_note: string;
  decided_at: string | null;
  threshold_at_decision: string | null;
  availability: string;
  routed_to: string;
  external_reference: string;
  external_decided_on: string | null;
  created_at: string;
}

export interface Filing {
  id: number;
  jurisdiction: string;
  office_name: string;
  international_justification: string;
  external_filing_id: string;
  filing_date: string;
  confirmation_reference: string;
  format_validation: string;
  created_at: string;
}

export interface Communication {
  id: number;
  kind: string;
  received_on: string;
  reference: string;
  details: string;
  created_at: string;
}

export interface OfficeAction {
  id: number;
  application_id: number;
  reference: string;
  received_on: string;
  response_due_on: string | null;
  current_due_on: string | null;
  requires_applicant_review: boolean;
  status: string;
  draft_response: string;
  approved_at: string | null;
  submitted_on: string | null;
  submission_reference: string;
  extensions: { new_due_on: string; reason: string }[];
}

export interface MaintenanceCycle {
  id: number;
  application_id: number;
  seq: number;
  due_on: string;
  source: string;
  status: string;
  deciding_director_user_id: number | null;
  director_name: string;
  decided_at: string | null;
  decision_note: string;
  action_reference: string;
  amount: string | null;
  actioned_on: string | null;
}

export interface Assessment {
  id: number;
  analysis: string;
  novelty: string;
  non_obviousness: string;
  utility: string;
  recommendation: string;
  status: string;
  finalized_at: string | null;
  updated_at: string;
}

export interface LegalRequest { id: number; kind: string; message: string; created_at: string }
export interface LegalAdvice { id: number; stage: string; advice: string; created_at: string }
export interface RevisionResponse {
  id: number; version: number; feedback_key: string; response: string; created_at: string;
}

export interface ApplicationDetail extends ApplicationRow {
  abstract: string;
  description: string;
  claims: string;
  preferred_attorney_user_id: number | null;
  version: number;
  decided_on: string | null;
  grant_date: string | null;
  grant_jurisdiction: string;
  patent_number: string;
  inventors: Inventor[];
  review_cycles: ReviewCycle[];
  appeals: Appeal[];
  attorney_assignments: Assignment[];
  budgets: Budget[];
  filings: Filing[];
  communications: Communication[];
  office_actions: OfficeAction[];
  maintenance_cycles: MaintenanceCycle[];
  assessments: Assessment[];
  legal_requests: LegalRequest[];
  legal_advice: LegalAdvice[];
  revision_responses: RevisionResponse[];
  relations: string[];
  feedback: Record<string, string>;
}

export interface AuditEntry {
  id: number;
  at: string;
  actor_user_id: number | null;
  actor_role: string;
  action: string;
  application_id: number | null;
  application_reference: string;
  object_type: string;
  object_id: number | null;
  from_state: string;
  to_state: string;
  details: Record<string, unknown>;
}

export interface DocumentVersion {
  id: number;
  number: number;
  original_name: string;
  size_bytes: number;
  sha256: string;
  uploaded_at: string;
  uploaded_by_user_id: number;
  is_current: boolean;
}

export interface PmsDocument {
  id: number;
  kind: string;
  title: string;
  sensitivity: string;
  versions: DocumentVersion[];
}

export interface Candidate { user_id: number; name: string; domain_codes: string[]; workload: number }

export interface RosterEntry {
  id: number;
  user_id: number;
  name: string;
  domain_codes: string[];
  valid_from: string;
  valid_to: string | null;
  workload: number;
}

export interface PriorArtReference {
  id: number;
  application_id: number;
  kind: string;
  title: string;
  identifier: string;
  url: string;
  source_name: string;
  notes: string;
  created_at: string;
}

export interface SearchResult {
  search_id: number;
  terms: string[];
  suggested_keywords: string[];
  classification_codes: string[];
  suggested_classifications: string[];
  sources: { code: string; label: string; status: string }[];
  results: { reference: PriorArtReference; score: number }[];
}

export interface LicensingRequest {
  id: number;
  application_id: number;
  application_reference: string;
  kind: string;
  summary: string;
  status: string;
  route_kind: string;
  routed_director_user_id: number | null;
  committee_name: string;
  routed_at: string | null;
  notes: { id: number; author_user_id: number; note: string; created_at: string }[];
  agreement: {
    id: number; counterparty: string; signed_on: string; terms_summary: string;
    financial_terms: string; financial_sync: string; created_at: string;
  } | null;
  created_at: string;
}

export interface WorkItem {
  kind: string; id: number; application_id: number; reference: string; title: string;
  status: string;
}

export interface Deadline {
  kind: string; subject_id: number; application_id: number; reference: string;
  due_on: string; responsible: string; missed: boolean;
}

export interface Escalation {
  id: number; kind: string; application_id: number; application_reference: string;
  subject_id: number; deadline: string | null; status: string; note: string;
  handled_at: string | null; created_at: string;
}

export interface Oversight {
  by_status: Record<string, number>; total: number; overdue_reviews: number;
  open_escalations: number;
}

export interface Report { columns: string[]; rows: Record<string, string | number>[] }

export interface ReportDefinition {
  id: number; name: string; report_type: string; filters: Record<string, string>;
  columns: string[]; schedule: string; active: boolean; created_at: string;
  runs: { id: number; period: string; created_at: string }[];
}

export interface Domain { code: string; label: string; ipc_classes: string[] }

export interface ReferenceData {
  domains: Domain[];
  sensitivities: string[];
  document_kinds: string[];
  alert_offsets_days: number[];
  withdrawal_statuses: string[];
  withdrawal_consent_required: boolean;
  report_types: string[];
  appeal_period_days: number;
}

export interface PolicyPayload {
  cost_threshold: string | null;
  appeal_period_days: number;
  alert_offsets_days: number[];
  withdrawal_statuses: string[];
  withdrawal_consent_required: boolean;
  holidays: string[];
  domains: Domain[];
  maintenance_rules: Record<string, number[]>;
  escalation_chain: number[];
  pcc_contact_user_id: number | null;
  auto_routing_enabled: boolean;
  licensing_route: { kind: string; director_user_id: number | null; committee_name: string } | null;
}

export interface Policy {
  version: number;
  payload: PolicyPayload;
  history: { version: number; effective_from: string; payload: PolicyPayload;
    published_by_user_id: number }[];
}

export interface Person { user_id: number; display_name: string; kind: string }
