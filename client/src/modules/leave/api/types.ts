/** Mirrors modules/leave/api/serializers.py; a field added there is added here. */

export type Category = "CL" | "RH" | "SCL" | "EL" | "COL" | "VL";
export type Half = "" | "first" | "second";

export interface LeaveEvent {
  id: number;
  event: string;
  from_status: string;
  to_status: string;
  actor_user_id: number | null;
  actor_role: string;
  outcome: string;
  remarks: string;
  at: string;
}

export interface Resumption {
  id: number;
  resumption_date: string;
  details: string;
  status: string;
  outcome: string;
  actual_end_date: string | null;
  adjustment_days: string | null;
  reviewed_at: string | null;
  review_remarks: string;
}

export interface SubstitutionRow {
  id: number;
  substitute_user_id: number;
  status: string;
  responded_at: string | null;
  remarks: string;
}

export interface LeaveRequest {
  id: number;
  kind: "new" | "cancellation" | "extension";
  parent_id: number | null;
  user_id: number;
  category: Category;
  category_label: string;
  start_date: string;
  end_date: string;
  half: Half;
  days: string;
  leave_year: number;
  status: string;
  status_label: string;
  purpose: string;
  station_leave: boolean;
  station_from: string | null;
  station_to: string | null;
  station_address: string;
  evidence_reference: string;
  applicant_kind: string;
  applicant_department: string;
  is_director_applicant: boolean;
  unit_head_outcome: string;
  decision: string;
  decided_role: string;
  decided_at: string | null;
  decision_remarks: string;
  source: "online" | "offline";
  offline_reference: string;
  submitted_at: string | null;
  withdrawn_at: string | null;
  created_at: string;
}

export interface LeaveRequestDetail extends LeaveRequest {
  events: LeaveEvent[];
  substitutions: SubstitutionRow[];
  resumption: Resumption | null;
  effective_end: string;
}

export interface Balance {
  category: Category;
  label: string;
  balance: string;
  pending: string;
  available: string;
  applicable: boolean;
}

export interface CategoryOption {
  category: Category;
  label: string;
  substitute: "required" | "optional" | "none";
  evidence_min_days: string | null;
  half_day: boolean;
  extendable: boolean;
}

export interface Overview {
  year: number;
  kind: string;
  department: string;
  balances: Balance[];
  categories: CategoryOption[];
  configured: boolean;
}

export interface LedgerEntry {
  id: number;
  leave_year: number;
  category: Category;
  delta: string;
  entry_type: string;
  entry_label: string;
  request_id: number | null;
  note: string;
  created_at: string;
}

export interface Page<T> {
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface Person {
  user_id: number;
  display_name: string;
  username: string;
  kind: string;
  department: string;
}

export type Action = "approve" | "reject" | "recommend" | "not_recommend" | "forward" | "review";

export interface QueueTask {
  id: number;
  step: string;
  assignee_designation: string;
  opened_at: string;
  reminded_at: string | null;
  escalated_at: string | null;
  request: LeaveRequest;
  applicant_name: string;
  actions: Action[];
  resumption: Resumption | null;
}

export interface SubstitutionRequest {
  id: number;
  status: string;
  created_at: string;
  request: LeaveRequest;
  applicant_name: string;
}

export interface Holiday {
  date: string;
  name: string;
  kind: "closed" | "restricted";
}

export interface Vacation {
  id: number;
  label: string;
  start_date: string;
  end_date: string;
  source_reference: string;
}

export interface EffectiveCalendar {
  year: number;
  published: boolean;
  holidays: Holiday[];
  vacations: Vacation[];
}

export interface HolidayCalendar {
  id: number;
  year: number;
  version: number;
  status: "draft" | "published" | "superseded";
  published_at: string | null;
  holidays: Holiday[];
}

export interface CategoryRule {
  category: Category;
  annual_entitlement: string;
  substitute: "required" | "optional" | "none";
  evidence_min_days: string | null;
}

export interface Policy {
  revision_id: number | null;
  rules: CategoryRule[];
  weekend_days: number[];
  max_backdate_days: number;
}

export interface OrgUnit {
  department: string;
  unit_head_designation: string;
  head_leave_designation: string;
}

export interface SanctionRoute {
  employee_kind: "" | "faculty" | "staff";
  category: string;
  department: string;
  applicant_designation: string;
  establishment_designation: string;
  sanction_designation: string;
}

export interface Hierarchy {
  revision_id: number | null;
  units: OrgUnit[];
  routes: SanctionRoute[];
  choices: Record<"unit_head" | "establishment" | "authority", string[]>;
  warnings: string[];
}

export interface SlaRule {
  step: string;
  reminder_hours: number;
  escalation_hours: number;
  action: "notify" | "reassign";
  escalate_to: string;
}

export interface EmployeeRecord {
  user_id: number;
  year: number;
  person: Person | null;
  balances: Balance[];
  requests: LeaveRequest[];
  ledger: LedgerEntry[];
}

export interface YearEndRun {
  year: number;
  status: string;
  accounts_processed: number;
  entries_written: number;
  exceptions: { user_id: number; reason: string }[];
  finished_at: string | null;
}

export interface Readiness {
  ready: boolean;
  unmet: string[];
  warnings: string[];
}

export interface ApplyInput {
  category: Category;
  start_date: string;
  end_date: string;
  half?: Half;
  purpose: string;
  station_leave?: boolean;
  station_from?: string | null;
  station_to?: string | null;
  station_address?: string;
  evidence_reference?: string;
  substitute_user_id?: number | null;
}
