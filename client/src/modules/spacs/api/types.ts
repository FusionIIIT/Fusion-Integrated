/** Wire types for the SPACS API. */

export interface Page<T> {
  results: T[];
  next: string | null;
  previous: string | null;
}

export type SchemeType = "scholarship" | "award";
export type TargetProgram = "all" | "ug" | "pg" | "phd";
export type EntryStatus = "draft" | "published" | "retired";
export type ApplicationStatus =
  | "draft"
  | "submitted"
  | "under_verification"
  | "flagged"
  | "correction_requested"
  | "verified"
  | "awarded"
  | "rejected"
  | "withdrawn";

export type AwardCycleStatus =
  | "pool_prepared"
  | "under_evaluation"
  | "evaluated"
  | "approved"
  | "published";

export interface CataloguePolicyVersion {
  id: number;
  entry: number;
  version_number: number;
  academic_year: string;
  financial_year: string;
  scheme_category: string;
  sponsor_agency: string;
  funding_source: string;
  is_renewable: boolean;
  max_renewal_terms: number;
  disbursement_frequency: string;
  sanctioned_seats: number | null;
  award_amount: string | null;
  frequency_amount: string | null;
  eligibility_schema: Record<string, unknown>;
  required_documents: Array<{ code: string; label: string; mandatory?: boolean }>;
  application_window_start: string | null;
  application_window_end: string | null;
  sla_verification_hours: number | null;
  sla_decision_hours: number | null;
  created_at: string;
}

export interface CatalogueEntry {
  id: number;
  code: string;
  name: string;
  type: SchemeType;
  status: EntryStatus;
  target_program: TargetProgram;
  award_committee: string;
  approving_authority: string;
  current_policy_version: CataloguePolicyVersion | null;
  versions?: CataloguePolicyVersion[];
  created_at: string;
  updated_at: string;
}

export interface ApplicationDocument {
  id: number;
  document_type: string;
  file_name: string;
  file_url: string;
  file_hash: string;
  is_reused: boolean;
  reused_from_application_id: number | null;
  verification_status: "pending" | "verified" | "flagged" | "rejected";
  verification_finding: string;
  verified_by: number | null;
  verified_at: string | null;
}

export interface ApplicationTransition {
  id: number;
  from_status: ApplicationStatus;
  to_status: ApplicationStatus;
  reason: string;
  created_by: number | null;
  created_at: string;
}

export interface ScholarshipApplication {
  id: number;
  application_number: string;
  student_id: number;
  catalogue_version: CataloguePolicyVersion;
  status: ApplicationStatus;
  academic_year: string;
  is_renewal: boolean;
  parent_application: number | null;
  renewal_count: number;
  submitted_at: string | null;
  verified_at: string | null;
  decided_at: string | null;
  decision_reason: string;
  correction_comments: string;
  concern_notes: string;
  form_data: Record<string, unknown>;
  documents: ApplicationDocument[];
  transitions?: ApplicationTransition[];
  created_at: string;
  updated_at: string;
}

export interface AwardCandidate {
  id: number;
  award_cycle: number;
  student_id: number;
  cpi: string | null;
  program: string;
  discipline: string;
  batch: string;
  evaluation_score: string | null;
  evaluation_notes: string;
  citation: string;
  merit_rank: number | null;
  is_selected: boolean;
  created_at: string;
}

export interface AwardCycle {
  id: number;
  catalogue_version: CataloguePolicyVersion;
  academic_year: string;
  convocation_year: string;
  status: AwardCycleStatus;
  approval_body: string;
  approved_by: number | null;
  approved_at: string | null;
  published_at: string | null;
  candidates?: AwardCandidate[];
  created_at: string;
  updated_at: string;
}

export interface SpacsAuditLog {
  id: number;
  event_type: string;
  actor_id: number | null;
  actor_role: string;
  target_model: string;
  target_id: string;
  reason: string;
  ip_address: string;
  timestamp: string;
  after_state?: Record<string, unknown>;
}
