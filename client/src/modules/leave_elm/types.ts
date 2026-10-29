export interface LeaveApplication {
  id: number;
  user_id: number;
  status: string;
  leave_type: number;
  start_date: string;
  end_date: string;
  purpose: string;
}

export interface LeaveBalance {
  id: number;
  user_id: number;
  leave_category: number;
  balance: string;
}

export interface LeaveTask {
  id: number;
  user_id: number;
  leave_application: number;
  task_type: string;
  status: string;
  title?: string; // Optional field
  description?: string; // Optional field
}

export interface LeaveHistory {
  id: number;
  status: string;
  decision: string;
}

export interface LeaveNotification {
  id: number;
  message: string;
}
