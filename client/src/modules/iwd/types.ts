export interface Complaint {
  id: number;
  requester_user_id: number;
  category: "Civil" | "Electrical";
  location: string;
  urgency: "Low" | "Medium" | "High" | "Urgent";
  remarks: string;
  assigned_engineer_id: number | null;
  status: string;
  assessment_details: string;
  assessment_date: string | null;
  is_urgent_escalated: boolean;
  urgent_remarks: string;
  is_resolved: boolean;
  resolved_at: string | null;
  rework_count: number;
  created_at: string;
  updated_at: string;
}

export interface Estimate {
  id: number;
  complaint: number;
  engineer_user_id: number;
  estimated_time_days: number;
  materials_details: string;
  total_cost: string;
  cost_band: "LOW" | "MID" | "HIGH";
  committee_outcome: string;
  committee_approved: boolean | null;
  dept_head_decision: string;
  dept_head_remarks: string;
  director_decision: string;
  director_remarks: string;
  rejection_reason: string;
  resubmission_count: number;
  status: string;
  created_at: string;
}

export interface InventoryItem {
  id: number;
  name: string;
  category: string;
  stock_quantity: number;
  unit: string;
  unit_price: string;
}

export interface FinalBill {
  id: number;
  complaint: number;
  engineer_user_id: number;
  total_amount: string;
  auditor_status: string;
  auditor_remarks: string;
  audited_at: string | null;
  director_approved: boolean;
  director_approved_at: string | null;
  accounts_settled: boolean;
  accounts_settled_at: string | null;
  settlement_reference: string;
  created_at: string;
}

export interface ComplaintFeedback {
  id: number;
  complaint: number;
  employee_user_id: number;
  rating: number;
  comments: string;
  post_repair_issue: boolean;
  post_repair_remarks: string;
  created_at: string;
}
