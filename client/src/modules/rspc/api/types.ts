/** TypeScript interfaces for RSPC domain models. */

export interface Proposal {
  id: number;
  user_id: number;
  title: string;
  proposal_type: "sponsored_research" | "consultancy";
  department: string;
  funding_agency: string;
  proposed_budget: string;
  overhead_amount: string;
  submission_deadline: string | null;
  status: "draft" | "submitted_hod" | "endorsed_hod" | "revision_requested" | "approved_dean" | "rejected";
  summary: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectBudgetHead {
  id: number;
  head_type: string;
  allocated_amount: string;
  spent_amount: string;
  committed_amount: string;
  available_balance: string;
}

export interface Project {
  id: number;
  project_code: string;
  project_type: "sponsored" | "consultancy";
  title: string;
  user_id: number;
  department: string;
  funding_agency: string;
  sanction_order_no: string;
  sanction_date: string;
  start_date: string;
  end_date: string;
  sanctioned_amount: string;
  status: "sanctioned" | "active" | "extension_requested" | "closure_pending" | "closed" | "terminated";
  budget_heads?: ProjectBudgetHead[];
  created_at: string;
  updated_at: string;
}

export interface ProjectFundTransaction {
  id: number;
  project_id: number;
  budget_head_id: number;
  head_type: string;
  transaction_type: "allocation" | "disbursement" | "reversal";
  amount: string;
  reference_no: string;
  description: string;
  created_by_user_id: number;
  created_at: string;
}
