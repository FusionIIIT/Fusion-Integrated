export interface LeaveApplication {
  id: number;
  user_id: number;
  kind: string;
  parent: number | null;
  category: string;
  start_on: string;
  end_on: string;
  half: string;
  purpose: string;
  chargeable_days: string;
  station_leave: boolean;
  station_details: string;
  medical_evidence: boolean;
  status: string;
  unit_code: string;
  requires_substitute: boolean;
  substitute_user_id: number | null;
  substitute_status: string;
  unit_head_recommendation: string;
  submitted_at: string | null;
  decided_at: string | null;
}

export interface Page<T> {
  count: number;
  results: T[];
}

export interface Balances {
  year: number;
  balances: Record<string, string>;
  history: Array<{
    id: number;
    category: string;
    year: number;
    amount: string;
    entry_type: string;
    memo: string;
    created_at: string;
  }>;
}

export interface LeavePolicy {
  id: number;
  version: number;
  label: string;
  is_effective: boolean;
  cl_annual: string;
  rh_annual: string;
  scl_annual: string;
  el_staff_annual: string;
  vl_faculty: string;
  col_annual: string;
}

export interface WorkflowTask {
  id: number;
  application: number;
  kind: string;
  status: string;
  assignee_role: string;
}
