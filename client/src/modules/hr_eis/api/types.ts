export interface EmployeeProfile {
  id: number;
  user_id: string;
  employee_id: string;
  full_name: string;
  email: string;
  department: string;
  designation: string;
  employment_type: "Faculty" | "Staff" | "Admin";
  date_of_joining: string;
  date_of_birth: string;
  retirement_date?: string;
  status: "Active" | "On_Leave" | "Retired" | "Suspended";
  is_hod: boolean;
}

export interface LeaveBalance {
  id: number;
  leave_type: string;
  year: number;
  entitled_days: string;
  used_days: string;
  available_days: number;
}

export interface LeaveRequest {
  id: number;
  leave_type: string;
  start_date: string;
  end_date: string;
  days_requested: string;
  reason: string;
  status: "Submitted" | "Recommended" | "Approved" | "Rejected" | "Cancelled";
  current_authority: string;
  remarks: string;
}

export interface AppraisalRecord {
  id: number;
  self_assessment: string;
  reviewer_comments: string;
  hod_remarks: string;
  director_remarks: string;
  overall_rating: string;
  status: string;
  is_immutable: boolean;
}

export interface LtcClaim {
  id: number;
  claim_type: "Advance" | "Reimbursement";
  block_year: string;
  destination: string;
  claimed_amount: string;
  approved_amount: string;
  status: string;
  hr_verification: string;
}

export interface CpdaClaim {
  id: number;
  claim_type: "Advance" | "Reimbursement";
  financial_year: string;
  purpose: string;
  claimed_amount: string;
  approved_amount: string;
  status: string;
  hr_verification: string;
}
