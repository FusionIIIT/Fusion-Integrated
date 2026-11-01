export interface ResearchProject {
  id: number;
  user_id: number;
  title: string;
  objectives: string;
  funding_source: string;
  budget_requested: string | null;
  start_date: string | null;
  end_date: string | null;
  resource_requirements: string;
  department: string;
  status: string;
  hod_remarks: string;
  admin_remarks: string;
  dean_remarks: string;
  director_remarks: string;
  submitted_at: string | null;
  hod_decided_at: string | null;
  admin_verified_at: string | null;
  dean_decided_at: string | null;
  director_decided_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConsultancyProject {
  id: number;
  user_id: number;
  title: string;
  client_name: string;
  client_details: string;
  scope: string;
  deliverables: string;
  financial_terms: string;
  total_amount: string | null;
  start_date: string | null;
  end_date: string | null;
  department: string;
  status: string;
  created_at: string;
}

export interface StaffAppointment {
  id: number;
  user_id: number;
  project: number | null;
  position_title: string;
  stipend_amount: string | null;
  duration_months: number | null;
  department: string;
  status: string;
  created_at: string;
}

export interface FinanceRequest {
  id: number;
  user_id: number;
  project: number | null;
  category: string;
  description: string;
  amount: string;
  purpose: string;
  status: string;
  created_at: string;
}

export interface ProcurementRequest {
  id: number;
  user_id: number;
  project: number | null;
  item_description: string;
  quantity: number;
  estimated_cost: string;
  justification: string;
  status: string;
  created_at: string;
}

export interface ProgressReport {
  id: number;
  user_id: number;
  project: number;
  reporting_period: string;
  summary: string;
  milestones_achieved: string;
  expenditure_so_far: string | null;
  status: string;
  created_at: string;
}

export interface ProjectClosure {
  id: number;
  user_id: number;
  project: number;
  completion_summary: string;
  financial_settlement_details: string;
  assets_declared: string;
  status: string;
  created_at: string;
}
