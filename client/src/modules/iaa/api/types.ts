export interface ExpenseItem {
  id: number;
  description: string;
  category: string;
  amount: string;
  receipt_reference: string;
  created_at: string;
}

export interface ExpenseVoucherRequest {
  id: number;
  user_id: number;
  department: string;
  request_type: "expense" | "voucher";
  title: string;
  description: string;
  total_amount: string;
  status:
    | "draft"
    | "submitted"
    | "query_raised"
    | "query_responded"
    | "finance_validated"
    | "approval_pending"
    | "approved"
    | "rejected"
    | "escalated"
    | "recorded";
  current_approval_level: number;
  required_approval_levels: number;
  assigned_approver_role: string;
  assigned_approver_id: number | null;
  approval_assigned_at: string | null;
  is_locked: boolean;
  items: ExpenseItem[];
  created_at: string;
  updated_at: string;
}

export interface TAExpenseItem {
  id: number;
  expense_type: string;
  amount: string;
  details: string;
  created_at: string;
}

export interface TAClaim {
  id: number;
  user_id: number;
  department: string;
  purpose: string;
  departure_date: string;
  arrival_date: string;
  source_location: string;
  destination_location: string;
  claimed_amount: string;
  status:
    | "submitted"
    | "query_raised"
    | "query_responded"
    | "verified"
    | "approval_pending"
    | "approved"
    | "rejected"
    | "escalated"
    | "recorded";
  is_high_value: boolean;
  assigned_approver_role: string;
  assigned_approver_id: number | null;
  approval_assigned_at: string | null;
  is_locked: boolean;
  items: TAExpenseItem[];
  created_at: string;
  updated_at: string;
}

export interface Anomaly {
  id: number;
  category: string;
  description: string;
  reference_type: string;
  reference_id: number;
  status: "open" | "resolved" | "escalated";
  flagged_by_id: number | null;
  flagged_by_role: string;
  resolver_role: string;
  resolved_by_id: number | null;
  resolution_remarks: string;
  created_at: string;
  resolved_at: string | null;
}

export interface AuditObservation {
  id: number;
  auditor_id: number;
  department: string;
  reference_type: string;
  reference_id: number | null;
  title: string;
  description: string;
  status: "open" | "responded" | "closed";
  response_text: string;
  responded_by_id: number | null;
  responded_at: string | null;
  closure_remarks: string;
  created_at: string;
  closed_at: string | null;
}

export interface IAAConfiguration {
  id: number;
  financial_year: string;
  high_value_ta_threshold: string;
  approval_timeout_days: number;
  is_active: boolean;
  updated_at: string;
}

export interface DepartmentBudget {
  id: number;
  department: string;
  financial_year: string;
  allocated_amount: string;
  utilized_amount: string;
  available_amount: string;
}

export interface DashboardSummary {
  requests: {
    total_count: number;
    total_amount: number;
    by_status: Record<string, number>;
  };
  travel: {
    total_count: number;
    total_amount: number;
    by_status: Record<string, number>;
  };
  anomalies: {
    total_count: number;
    by_status: Record<string, number>;
  };
  audit: {
    total_count: number;
    by_status: Record<string, number>;
  };
}
