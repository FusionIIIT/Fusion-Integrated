export interface MessRoleAssignment {
  id: number;
  mess_name: string;
  role: string;
  employee_id: number;
  is_active: boolean;
  assigned_date: string;
}

export interface RegistrationWindow {
  id: number;
  semester: string;
  start_date: string;
  end_date: string;
  is_open: boolean;
}

export interface MessRegistration {
  id: number;
  student_id: number;
  mess_name: string;
  status: string;
  registered_date: string;
  rejection_reason?: string;
}

export interface DailyMenuItem {
  id: number;
  mess_name: string;
  day_of_week: string;
  meal_time: string;
  menu_description: string;
}

export interface RebateRequest {
  id: number;
  student_id: number;
  mess_name: string;
  start_date: string;
  end_date: string;
  duration_days: number;
  reason: string;
  status: string;
  review_notes?: string;
}

export interface MessFeedback {
  id: number;
  student_id: number;
  mess_name: string;
  category: string;
  comment: string;
  is_addressed: boolean;
}

