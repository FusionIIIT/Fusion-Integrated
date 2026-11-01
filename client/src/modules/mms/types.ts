export interface MessRoleAssignment {
  id: number;
  employee_id: number;
  role: string;
  start_date: string;
  end_date: string | null;
  is_active: boolean;
  assigned_by_id: number | null;
  remarks: string;
  created_at: string;
}

export interface RegistrationWindow {
  id: number;
  name: string;
  mess_name: string;
  start_date: string;
  end_date: string;
  is_open: boolean;
  opened_by_id: number;
  created_at: string;
}

export interface MessRegistration {
  id: number;
  student_id: number;
  window_id: number | null;
  mess_name: string;
  start_date: string;
  end_date: string | null;
  status: "PENDING" | "REGISTERED" | "REJECTED" | "DEREGISTERED";
  remarks: string;
  reviewed_by_id: number | null;
  deregistration_date: string | null;
  deregistration_reason: string;
  created_at: string;
}

export interface DailyMenuItem {
  id: number;
  mess_name: string;
  day_of_week: string;
  meal_time: string;
  items: string;
  is_active: boolean;
  updated_by_id: number | null;
  updated_at: string;
}

export interface RebateRequest {
  id: number;
  student_id: number;
  mess_name: string;
  start_date: string;
  end_date: string;
  duration_days: number;
  reason: string;
  status: "PENDING" | "APPROVED" | "REJECTED";
  approved_start_date: string | null;
  approved_end_date: string | null;
  reviewed_by_id: number | null;
  decision_remarks: string;
  created_at: string;
}

export interface MessFeedback {
  id: number;
  student_id: number;
  mess_name: string;
  rating: number;
  category: string;
  comments: string;
  is_resolved: boolean;
  resolution_notes: string;
  created_at: string;
}
