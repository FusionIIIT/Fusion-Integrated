
/** Wire types for the SPACS API.
 *
 * These interfaces follow the backend DRF serializers in:
 * modules/spacs/api/serializers.py
 */

export interface Page<T> {
  results: T[];
  next: string | null;
  previous: string | null;
}

// -----------------------------------------------------------------------------
// Common types
// -----------------------------------------------------------------------------

export type SchemeType = "scholarship" | "award";

export type EntryStatus = "draft" | "published" | "retired";

/**
 * Application lifecycle values are controlled by the backend state machine.
 * Keep this open to accommodate configured workflow states.
 */
export type ApplicationStatus = string;

export type AwardCycleStatus = string;

// -----------------------------------------------------------------------------
// Catalogue and policy
// -----------------------------------------------------------------------------

export interface CataloguePolicyVersion {
  id: number;
  version_label: string;

  effective_from: string;
  effective_to: string | null;

  policy_approval_ref: string;
  policy_approval_date: string | null;

  application_window_start: string | null;
  application_window_end: string | null;

  is_renewable: boolean;
  renewal_window_start: string | null;
  renewal_window_end: string | null;
  max_renewal_cycles: number;

  candidate_source_method: string;
  eval_committee_role: string;
  approving_authority_title: string;

  eligibility_schema: Record<string, unknown>;
  required_evidence_schema: unknown[];
  sla_config: Record<string, unknown>;

  is_published: boolean;
}

export interface CatalogueEntry {
  id: number;
  code: string;
  title: string;
  kind: SchemeType;
  description: string;
  status: EntryStatus;

  active_version: CataloguePolicyVersion | null;
  versions?: CataloguePolicyVersion[];
}

// -----------------------------------------------------------------------------
// Scholarship application documents
// -----------------------------------------------------------------------------

export interface ApplicationDocument {
  id: number;

  doc_type: string;
  title: string;

  drive_url: string;
  drive_file_id: string;

  declared_validity_date: string | null;

  is_reused: boolean;
  reused_from_doc_id: number | null;

  verification_status: string;
  verification_comment: string;
}

// -----------------------------------------------------------------------------
// Application timeline
// -----------------------------------------------------------------------------

export interface ApplicationTransition {
  from_status: string;
  to_status: string;

  actor_user_id: string | null;
  actor_role_label: string;

  reason: string;
  at: string;
}

export interface ApplicationTimeline {
  application_id: number;
  timeline: ApplicationTransition[];
}

// -----------------------------------------------------------------------------
// Scholarship applications
// -----------------------------------------------------------------------------

export interface ScholarshipApplication {
  id: number;
  application_number: string;

  user_id: string;

  scheme_code: string;
  scheme_title: string;
  academic_cycle: string;

  status: ApplicationStatus;

  is_renewal: boolean;
  renewal_cycle_number: number;

  submitted_at: string | null;
  created_at: string;

  // Additional fields available in the detail serializer.
  prior_award_id?: string | null;

  applicant_snapshot?: Record<string, unknown>;
  submission_data?: Record<string, unknown>;

  documents?: ApplicationDocument[];

  verified_at?: string | null;
  verification_findings?: Record<string, unknown>;
  verification_concern_note?: string;

  decision_outcome?: string;
  decision_reason?: string;
  decision_at?: string | null;

  withdrawn_at?: string | null;
  withdrawn_reason?: string;

  policy_version_detail?: CataloguePolicyVersion;
}

// -----------------------------------------------------------------------------
// Convocation award candidates
// -----------------------------------------------------------------------------

export interface AwardCandidate {
  id: number;

  award_cycle_id: number;
  user_id: string;

  source_method: string;

  academic_snapshot: Record<string, unknown>;
  nomination_data: Record<string, unknown>;

  is_eligible: boolean;
  ineligibility_notes: string;

  evaluation_score: string | null;

  committee_recommendation: string;
  committee_remarks: string;

  is_final_winner: boolean;
}

// -----------------------------------------------------------------------------
// Award cycles
// -----------------------------------------------------------------------------

export interface AwardCycle {
  id: number;

  policy_version_id: number;

  award_title: string;
  convocation_year: number;

  status: AwardCycleStatus;

  pool_finalized_at: string | null;
  eval_completed_at: string | null;

  approval_authority_recorded: string;
  approval_reference_recorded: string;
  approval_recorded_at: string | null;

  published_at: string | null;

  candidates?: AwardCandidate[];

  created_at: string;
}

// -----------------------------------------------------------------------------
// Audit trail
// -----------------------------------------------------------------------------

export interface SpacsAuditLog {
  id: number;

  action: string;

  entity_type: string;
  entity_id: string;

  actor_user_id: string | null;
  actor_role: string;

  details: Record<string, unknown>;

  ip_address: string;

  created_at: string;
}
