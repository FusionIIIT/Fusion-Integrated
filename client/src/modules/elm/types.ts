interface LeaveType {
  code: string;
  name: string;
  description: string;
  annual_quota: number;
  is_vacation: boolean;
  max_continuous_days: number;
}

interface LeaveBalance {
  id: number;
  user: string;
  leave_type: LeaveType;
  year: number;
  credited_days: number;
  used_days: number;
  balance: number;
}

interface LeaveActionLog {
  id: number;
  leave_request: LeaveRequest;
  actor: string;
  role_name: string;
  action: string;
  comments: string;
  created_at: Date;
}

interface LeaveRequest {
  id: number;
  applicant: string;
  leave_type: LeaveType;
  start_date: Date;
  end_date: Date;
  half_day: boolean;
  half_day_period: string;
  purpose: string;
  station_leave: boolean;
  station_leave_address: string;
  substitute: string;
  substitute_status: string;
  status: string;
  action_logs: LeaveActionLog[];
  created_at: Date;
}