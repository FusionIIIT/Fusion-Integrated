/** Wire types for the placement API. Two shapes carry meaning:
 *
 *  * `AcademicStanding` is null when there is no DECLARED result — never a
 *    zero CPI, and the UI must not render it as one.
 *  * Money and CPI arrive as STRINGS, as Django serialises Decimal. Parsing
 *    them into JS numbers puts float arithmetic on a salary figure.
 */

export interface Page<T> {
  results: T[];
  next: string | null;
  previous: string | null;
}

export interface CompanyBrief {
  id: number;
  name: string;
  slug: string;
  sector: string;
  /** Policy rules 2.B and 10 turn on this, not on the free-text `sector`. */
  sector_kind: "it" | "core" | "other";
  website: string;
  hq_city: string;
  tier_rank: number | null;
  /** Rule 8 — once placed here, no switching out, whatever is offered. */
  is_marquee: boolean;
}

export interface Company extends CompanyBrief {
  status: "prospect" | "active" | "blacklisted";
  approval_status: "pending" | "approved" | "rejected";
  approval_note: string;
  approved_at: string | null;
  can_operate: boolean;
  contacts: CompanyContact[];
  created_at: string;
}

export interface CompanyContact {
  id: number;
  name: string;
  designation: string;
  email: string;
  phone: string;
  is_primary: boolean;
}

export type PostingStatus =
  | "draft" | "pending_approval" | "published" | "closed"
  | "in_progress" | "completed" | "cancelled";

export interface Posting {
  id: number;
  title: string;
  kind: "fte" | "internship" | "ppo";
  company: CompanyBrief;
  placement_year: string;
  description: string;
  location: string;
  ctc_lpa: string | null;
  stipend_pm: string | null;
  bond_months: number | null;
  seats: number | null;
  eligibility_rule: Record<string, unknown>;
  /** Rule 7 — a Dream Slot is open to placed students as well as unplaced. */
  is_dream_slot: boolean;
  dream_slot_note: string;
  status: PostingStatus;
  opens_at: string | null;
  closes_at: string | null;
  published_at: string | null;
  is_open: boolean;
  created_at: string;
}

export type ApplicationStatus =
  | "draft" | "submitted" | "under_review" | "shortlisted"
  | "interview_scheduled" | "selected" | "rejected" | "withdrawn"
  | "auto_withdrawn" | "offer_issued" | "offer_accepted" | "offer_declined"
  | "offer_expired";

export interface Candidate {
  user_id: number;
  name: string;
  roll_no: string;
  discipline: string;
  programme: string;
  batch_year: number | null;
}

/** Why a student is (not) eligible. Every failure carries a rendered message
 *  so the UI never has to compose one from a code. */
export interface EligibilityFailure {
  field: string;
  reason: string;
  required: unknown;
  actual: unknown;
  message: string;
}

export interface AcademicStanding {
  semester: number | null;
  semester_type: string | null;
  declared_seq: number | null;
  synced_at: string | null;
  computed_by: string | null;
}

export interface EligibilityVerdict {
  is_eligible: boolean;
  failed: EligibilityFailure[];
  error: string | null;
  season_decision: { allowed: boolean; rule: string; message: string };
  /** null means NO DECLARED RESULT — not a CPI of zero. */
  cpi: string | null;
  semester: number | null;
  declared_seq: number | null;
  standing: AcademicStanding;
  evaluated_at: string;
}

export interface Application {
  id: number;
  posting: Posting;
  user_id: number;
  status: ApplicationStatus;
  cpi_at_apply: string | null;
  semester_at_apply: number | null;
  eligibility_snapshot: Partial<EligibilityVerdict>;
  cover_note: string;
  applied_at: string | null;
  withdrawn_reason: string;
  allowed_transitions: ApplicationStatus[];
  candidate: Candidate | null;
  created_at: string;
}

/** What a recruiter sees. Narrower on purpose — no eligibility snapshot, no
 *  withdrawal reasons, no audit trail. */
export interface Applicant {
  id: number;
  status: ApplicationStatus;
  cpi_at_apply: string | null;
  semester_at_apply: number | null;
  cover_note: string;
  applied_at: string | null;
  candidate: Candidate;
}

export interface Offer {
  id: number;
  posting: Posting;
  user_id: number;
  ctc_lpa: string | null;
  tier_rank: number | null;
  is_dream: boolean;
  status: "issued" | "accepted" | "declined" | "revoked" | "superseded"
    | "expired";
  respond_by: string;
  responded_at: string | null;
  policy_decision: {
    allowed?: boolean; rule?: string; message?: string;
    facts?: Record<string, unknown>;
  };
  created_at: string;
}

export interface InterviewRound {
  id: number;
  posting: number;
  seq: number;
  kind: "test" | "gd" | "tech" | "hr" | "other";
  mode: "online" | "offline";
  starts_at: string;
  ends_at: string | null;
  venue: string;
  meeting_url: string;
  capacity: number | null;
  instructions: string;
  created_at: string;
}

export interface Announcement {
  id: number;
  title: string;
  body: string;
  topic: "drive" | "company_visit" | "training" | "workshop" | "internship"
    | "general";
  audience: "students" | "registered" | "alumni" | "all";
  placement_year: string;
  published_at: string | null;
  published_by_role: string;
  is_withdrawn: boolean;
  withdrawn_reason: string;
  created_at: string;
}

export interface ProfileDocument {
  id: number;
  kind: "resume" | "certificate" | "offer_letter" | "other";
  title: string;
  original_filename: string;
  /** True for a Drive link, false for a row from the old upload path. */
  is_link: boolean;
  /** The authorising endpoint, never the Drive URL itself. */
  download_url: string;
  content_type: string;
  size_bytes: number | null;
  created_at: string;
}

export interface MissingField {
  field: string;
  label: string;
  weight: number;
}

export interface StudentProfile {
  user_id: number;
  headline: string;
  about: string;
  phone: string;
  alternate_email: string;
  skills: string[];
  achievements: string[];
  certifications: string[];
  experience: unknown[];
  projects: unknown[];
  education: unknown[];
  github_url: string;
  linkedin_url: string;
  portfolio_url: string;
  completeness_percent: number;
  is_complete: boolean;
  missing_fields: MissingField[];
  documents: ProfileDocument[];
  updated_at: string;
  /** Present only on the placeholder the server returns before a profile
   *  exists. */
  exists?: boolean;
}

/** Anonymised figures a student may see. `available: false` when there are too
 *  few placements to publish without identifying people. */
export interface StudentStats {
  season: string;
  available: boolean;
  reason?: string;
  registered?: number;
  placed?: number;
  placement_rate?: number | null;
  companies_participated?: number;
  median_ctc?: string | null;
  max_ctc?: string | null;
  companies?: { company: string; placed: number }[];
  computed_at?: string;
}

export interface StaffStats {
  season: string;
  available: boolean;
  registered?: number;
  debarred?: number;
  placed?: number;
  median_ctc?: string | null;
  mean_ctc?: string | null;
  max_ctc?: string | null;
  by_company?: { company__name: string; placed: number; top: string | null }[];
  applications_by_status?: Record<string, number>;
}
