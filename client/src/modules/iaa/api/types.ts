// client/src/modules/iaa/api/types.ts

export interface ExpenseRequest {
  id: number;
  title: string;
  description: string;
  department: string;
  amount: string;
  status: 'draft' | 'submitted' | 'under_review' | 'clarification_requested' | 'approved' | 'rejected' | 'completed' | 'escalated';
  creator_user_id: string;
  creator_role: string;
  current_authority_role: string;
  current_authority_user_id: string;
  is_locked: boolean;
  submission_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface TravelAllowanceClaim {
  id: number;
  claimant_user_id: string;
  claimant_role: string;
  purpose: string;
  travel_start_date: string;
  travel_end_date: string;
  departure_location: string;
  destination_location: string;
  total_amount: string;
  is_high_value: boolean;
  status: 'draft' | 'submitted' | 'under_review' | 'clarification_requested' | 'approved' | 'rejected' | 'completed';
  current_authority_role: string;
  current_authority_user_id: string;
  is_locked: boolean;
  created_at: string;
  updated_at: string;
}

export interface DepartmentBudget {
  id: number;
  department: string;
  fiscal_year: string;
  allocated_budget: string;
  committed_budget: string;
  spent_budget: string;
  available_budget?: string;
  created_at: string;
  updated_at: string;
}

export interface AnomalyRecord {
  id: number;
  category: string;
  description: string;
  department: string;
  status: 'open' | 'investigating' | 'resolved' | 'escalated';
  detected_at: string;
  resolved_at: string | null;
  resolution_notes: string;
}

export interface AuditObservation {
  id: number;
  observation_title: string;
  observation_details: string;
  department: string;
  auditor_user_id: string;
  status: 'issued' | 'response_submitted' | 'closed';
  department_response: string;
  closure_remarks: string;
  created_at: string;
  closed_at: string | null;
}

export interface ApprovalAction {
  id: number;
  request_type: string;
  request_id: number;
  actor_user_id: string;
  actor_role: string;
  action: string;
  remarks: string;
  timestamp: string;
}