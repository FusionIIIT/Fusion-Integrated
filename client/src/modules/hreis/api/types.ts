/** Types for HR-EIS (Human Resource - Employee Information System) module. */

export interface EmployeeServiceRecord {
  id: number;
  user_id: number;
  employee_id: string;
  department: string;
  designation: string;
  category: "faculty" | "staff";
  appointment_date: string | null;
  retirement_date: string | null;
  retirement_status: "active" | "retired" | "resigned";
  service_history: Array<{
    designation: string;
    department: string;
    start_date: string;
    end_date?: string;
  }>;
  leave_balances: Record<string, number>;
  cpda_balance: string | number;
  ltc_eligible_block: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface LeaveRequest {
  id: number;
  user_id: number;
  leave_type: "casual" | "restricted" | "medical" | "earned" | "vacation" | "sabbatical";
  start_date: string;
  end_date: string;
  duration_days: number;
  justification: string;
  status: "pending" | "forwarded" | "approved" | "rejected";
  current_authority_role: string;
  decision_history: Array<{
    role: string;
    actor_id: number;
    actor_username: string;
    outcome: string;
    remarks: string;
    timestamp: string;
  }>;
  created_at: string;
  updated_at: string;
}

export interface AppraisalSubmission {
  id: number;
  user_id: number;
  academic_year: string;
  status: "draft" | "submitted" | "under_review" | "finalized";
  content: {
    teaching_engagement?: unknown;
    research_publications?: unknown;
    sponsored_projects?: unknown;
    administrative_responsibilities?: unknown;
    self_appraisal_summary?: string;
    [key: string]: unknown;
  };
  assigned_reviewers: number[];
  reviews: Array<{
    reviewer_id: number;
    reviewer_username: string;
    reviewer_role: string;
    score: number;
    comments: string;
    timestamp: string;
  }>;
  final_score: number | null;
  final_remarks: string;
  finalized_at: string | null;
  is_immutable: boolean;
  created_at: string;
  updated_at: string;
}

export interface LtcRequest {
  id: number;
  user_id: number;
  request_type: "advance" | "reimbursement";
  block_year: string;
  travel_from: string;
  travel_to: string;
  travel_start_date: string;
  travel_end_date: string;
  estimated_amount: string | number;
  claimed_amount: string | number | null;
  passed_amount: string | number | null;
  supporting_documents: Array<{ name: string; url: string }>;
  verification_status: "pending_verification" | "verified" | "returned" | "rejected";
  verification_remarks: string;
  status: "submitted" | "verified" | "forwarded" | "approved" | "rejected" | "returned" | "settled";
  current_authority_role: string;
  approval_history: Array<{
    role: string;
    actor_id: number;
    actor_username: string;
    outcome: string;
    remarks: string;
    timestamp: string;
  }>;
  payment_status: "unpaid" | "processing" | "paid";
  payment_reference: string;
  settlement_details: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface CpdaRequest {
  id: number;
  user_id: number;
  request_type: "advance" | "reimbursement";
  purpose: string;
  amount: string | number;
  passed_amount: string | number | null;
  supporting_documents: unknown[];
  verification_status: "pending_verification" | "verified" | "returned" | "rejected";
  verification_remarks: string;
  status: "submitted" | "verified" | "forwarded" | "approved" | "rejected" | "returned" | "settled";
  current_authority_role: string;
  approval_history: Array<{
    role: string;
    actor_id: number;
    actor_username: string;
    outcome: string;
    remarks: string;
    timestamp: string;
  }>;
  disbursement_status: "unpaid" | "processing" | "paid";
  disbursement_details: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface WorkflowConfiguration {
  setting_key: string;
  setting_value: Record<string, unknown>;
  description: string;
  updated_at: string;
}

export interface HrAuditLog {
  id: number;
  actor_id: number;
  actor_username: string;
  actor_role: string;
  action: string;
  entity_type: string;
  entity_id: string;
  details: Record<string, unknown>;
  ip_address: string;
  timestamp: string;
}

export interface HrNotification {
  id: number;
  user_id: number;
  title: string;
  message: string;
  category: "submission" | "approval" | "rejection" | "forwarding" | "reminder" | "policy";
  link: string;
  is_read: boolean;
  created_at: string;
}

export interface DashboardStats {
  leave_balances?: Record<string, number>;
  cpda_balance?: number;
  ltc_eligible_block?: string;
  pending_leaves_count: number;
  pending_ltc_count: number;
  pending_cpda_count: number;
  pending_reviews_count: number;
}
