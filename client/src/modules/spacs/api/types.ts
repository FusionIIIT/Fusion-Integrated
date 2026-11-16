/** Wire types for the SPACS API. */

export interface Scheme {
  id: number;
  scheme_code: string;
  name: string;
  scheme_type: "scholarship" | "award";
  description: string;
  status: "draft" | "published" | "retired";
  min_cpi: string;
  max_family_income: string | null;
  academic_cycle: string;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface AwardCycle {
  id: number;
  catalogue_entry_id: number;
  academic_cycle: string;
  state: "open" | "pool_prepared" | "under_committee_evaluation" | "committee_result_recorded" | "awaiting_approval" | "ready_for_publication" | "published";
  criteria_version: number;
  approval_evidence: string;
  published_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Application {
  id: number;
  application_id: string;
  catalogue_entry_id: number;
  applicant_user_id: number;
  academic_cycle: string;
  is_renewal: boolean;
  state: string;
  cpi: string | null;
  family_income: string | null;
  submitted_at: string | null;
  verification_findings: string;
  correction_reason: string;
  decision_reason: string;
  decision_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AwardCandidate {
  id: number;
  award_cycle_id: number;
  student_user_id: number;
  cpi: string;
  academic_standing: string;
  shortlisted: boolean;
  evaluation_score: string | null;
  committee_recommendation: string;
  remarks: string;
}

export interface SpacsTask {
  id: number;
  task_type: string;
  entity_type: string;
  entity_id: string;
  assigned_role: string;
  assigned_user_id: number | null;
  status: string;
  due_at: string | null;
  created_at: string;
}
