export interface LeaveType {
  id: number;
  code: string;
  name: string;
  description: string;
  annual_quota: string;
  carries_forward: boolean;
  is_active: boolean;
}

export interface LeaveBalance {
  id: number;
  user_id: number;
  leave_type: number;
  leave_type_name: string;
  leave_type_code: string;
  balance: string;
  year: number;
}

export interface LeaveApplication {
  id: number;
  user_id: number;
  leave_type: number;
  leave_type_name: string;
  leave_type_code: string;
  start_date: string;
  end_date: string;
  reason: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface LeaveApproval {
  id: number;
  user_id: number;
  approver_user_id: number;
  leave_application: number;
  stage: number;
  decision: string;
  comments: string;
  decided_at: string | null;
  created_at: string;
}
