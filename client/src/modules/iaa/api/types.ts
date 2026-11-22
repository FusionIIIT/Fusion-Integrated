export interface Page<T> {
  results: T[];
  next: string | null;
  previous: string | null;
}

export type RecordKind = "expense" | "ta";

export interface Document { id: number; title: string; link: string; created_at: string }

export interface Query {
  id: number; question: string; raised_role: string; response: string;
  responded_at: string | null; created_at: string;
}

export interface Step {
  id: number; level: number; designation: string; status: string; assigned_at: string;
  via_escalation: boolean; decided_role: string; decided_at: string | null; remarks: string;
}

export interface FinancialRecord {
  id: number; kind: RecordKind; status: string; user_id: number; department: string;
  request_type: string; title: string; description: string; amount: string | null;
  purpose: string; trip_start: string | null; trip_end: string | null;
  financial_year: string | null; submitted_at: string | null; route_levels: string[];
  current_level: number | null; processing_reference: string; processing_note: string;
  processed_at: string | null; created_at: string; updated_at: string;
}

export interface RecordDetail extends FinancialRecord {
  documents: Document[]; queries: Query[]; steps: Step[];
}

export interface TrailEntry {
  id: number; action: string; from_status: string; to_status: string;
  actor_user_id: number | null; actor_role: string; remarks: string; created_at: string;
}

export interface Anomaly {
  id: number; record: number | null; category: string; source: string; description: string;
  status: string; resolver_chain: string[]; resolver_level: number; assigned_role: string;
  raised_role: string; resolved_role: string; resolved_at: string | null; resolution: string;
  created_at: string;
}

export interface ObservationResponse {
  id: number; cycle: number; corrective_action: string; evidence_link: string;
  verdict: string; review_remarks: string; reviewed_at: string | null; created_at: string;
}

export interface Observation {
  id: number; record: number | null; respondent_user_id: number; title: string; detail: string;
  status: string; cycle: number; raised_role: string; created_at: string;
  responses: ObservationResponse[];
}

export interface Summary {
  records: { kind: string; status: string; count: number }[];
  approval_turnaround: { designation: string; decisions: number; average_hours: number }[];
  anomalies: { category: string; status: string; count: number }[];
  observations: { status: string; count: number }[];
}

export interface Dashboard {
  pending: Record<string, number>;
  notifications: { id: number; kind: string; message: string; entity: string;
                   entity_id: number; created_at: string }[];
}

export interface PolicyVersion {
  id: number; effective_from: string; approval_timeout_hours: number;
  ta_high_value_threshold: string; budget_check_required: boolean; request_types: string[];
  required_documents: Record<string, number>; routes: unknown[];
  anomaly_resolvers: Record<string, string[]>; created_role: string; created_at: string;
}

export interface FinancialYear { id: number; code: string; starts_on: string; ends_on: string }

export interface BudgetEntry {
  id: number; financial_year: string; department: string; kind: string; amount: string;
  record: number | null; note: string; created_at: string;
}
