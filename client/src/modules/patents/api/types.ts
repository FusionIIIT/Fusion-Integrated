// Wire types for the patents API mirroring Django serializers (decimals serialized as strings).

export interface Page<T> {
  results: T[];
  next: string | null;
  previous: string | null;
}

export type PatentApplicationStatus =
  | "DRAFT"
  | "SUBMITTED"
  | "DIRECTOR_ASSIGNED"
  | "UNDER_REVIEW"
  | "NEEDS_REVISION"
  | "RESUBMITTED"
  | "APPROVED"
  | "REJECTED"
  | "APPEAL_SUBMITTED"
  | "APPEALED"
  | "DECISION_MODIFIED"
  | "ATTORNEY_ASSIGNED"
  | "PENDING_REVIEW"
  | "ASSESSMENT_IN_PROGRESS"
  | "BUDGET_PENDING"
  | "FILED"
  | "OFFICE_ACTION_PENDING"
  | "RESPONSE_SUBMITTED"
  | "GRANTED"
  | "WITHDRAWN"
  | "ABANDONED"
  | "EXPIRED";

export interface CoInventor {
  id: number;
  user_id?: number | null;
  name: string;
  email: string;
  share_percentage: string;
  consent_granted: boolean;
  consent_timestamp: string | null;
}

export interface ApplicationDocument {
  id: number;
  document_type: string;
  file_name: string;
  file_format: string;
  file_size_bytes: number;
  sensitivity_level: string;
  version: number;
  uploaded_by_user_id: number;
  created_at: string;
}

export interface ReviewDecision {
  id: number;
  director_user_id: number;
  decision: "APPROVE" | "REJECT" | "REQUEST_REVISIONS";
  justification: string;
  assigned_at: string;
  decided_at: string | null;
}

export interface AppealRecord {
  id: number;
  applicant_user_id: number;
  grounds: string;
  status: "PENDING" | "REMANDED" | "UPHELD" | "MODIFIED";
  director_user_id: number | null;
  decision_notes: string;
  submitted_at: string;
  decided_at: string | null;
}

export interface BudgetLedgerEntry {
  id: number;
  entry_type: "FILING" | "PROSECUTION" | "MAINTENANCE" | "LEGAL";
  amount: string;
  currency: string;
  category: string;
  status: "REQUESTED" | "APPROVED" | "REJECTED" | "EXPENDED";
  authorized_by_user_id: number | null;
  notes: string;
  created_at: string;
}

export interface OfficeActionRecord {
  id: number;
  action_code: string;
  issuing_authority: string;
  issued_date: string;
  response_deadline: string;
  status: "PENDING" | "RESPONDED" | "CLOSED";
  requires_applicant_review: boolean;
  response_summary: string;
  submitted_at: string;
}

export interface TechnologyTransferRecord {
  id: number;
  applicant_user_id: number;
  request_type: string;
  partner_name: string;
  status: "SUBMITTED" | "UNDER_NEGOTIATION" | "EXECUTED" | "TERMINATED";
  confidentiality_level: string;
  terms_summary: string;
  created_at: string;
}

export interface PatentApplicationSummary {
  id: number;
  application_number: string;
  user_id: number;
  title: string;
  status: PatentApplicationStatus;
  domain_category: string;
  assigned_director_id: number | null;
  assigned_attorney_id: number | null;
  external_filing_id: string;
  jurisdiction: string;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface RenewalHistoryEntry {
  id: number;
  cycle_due_date: string | null;
  requested_at: string | null;
  decision: "RENEW" | "DO_NOT_RENEW";
  decided_by_user_id: number;
  decided_at: string;
  action_reference: string;
  action_recorded_at: string | null;
  next_due_date: string | null;
}

export interface PatentApplicationDetail extends PatentApplicationSummary {
  abstract: string;
  description: string;
  claims: string;
  filing_date: string | null;
  filing_office: string;
  filing_confirmation: string;
  filing_justification: string;
  grant_date: string | null;
  renewal_decision: "" | "RENEW" | "DO_NOT_RENEW";
  maintenance_state: "" | "ACTIVE" | "DECISION_REQUESTED" | "RENEWAL_APPROVED" | "DO_NOT_RENEW" | "RENEWED";
  renewal_requested_at: string | null;
  renewal_history: RenewalHistoryEntry[];
  decision_date: string | null;
  co_inventors: CoInventor[];
  documents: ApplicationDocument[];
  reviews: ReviewDecision[];
  appeals: AppealRecord[];
  budget_entries: BudgetLedgerEntry[];
  office_actions: OfficeActionRecord[];
  licensing_records: TechnologyTransferRecord[];
}

export interface CreateApplicationInput {
  title: string;
  abstract?: string;
  description?: string;
  claims?: string;
  domain_category: string;
  jurisdiction?: string;
  co_inventors?: CoInventor[];
}

export interface AttorneyPanelMember {
  id: number;
  user_id: number;
  firm_name: string;
  expertise_domains: Record<string, unknown> | string[];
  active_workload: number;
  is_approved_panel: boolean;
}

export interface PriorArtResult {
  query: string;
  results: string[];
}

export interface ReportsResponse {
  total_applications: number;
  filed_count: number;
  granted_count: number;
}

export interface AuditLogsResponse {
  audit_logs: string[];
}
