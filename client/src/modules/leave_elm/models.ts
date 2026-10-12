export interface LeaveApplication {
  id?: number;
  category: string;
  start_date: string;
  end_date: string;
  purpose?: string;
  station_leave_required?: boolean;
  substitute_user_id?: number;
  status?: string;
  final_decision_type?: string;
  final_decision_date?: string | null;
  created_at?: string;
}

export interface LeaveBalance {
  effective_date: string;
  cl_balance: number;
  rh_balance: number;
  scl_balance: number;
  el_balance: number;
  col_balance: number;
  vl_balance: number;
}

export interface WorkflowTask {
  id?: number;
  task_type: string;
  assigned_to_user_id?: number;
  status?: string;
  reminder_threshold_seconds?: number;
  escalation_threshold_seconds?: number;
  last_reminder_sent_at?: string | null;
  last_escalation_sent_at?: string | null;
}
