/** Wire types for the MMS API. */

export interface SpecialFoodRequest {
  id: number;
  user_id: number;
  student_user_id: number;
  reason: string;
  requested_date: string;
  status: "requested" | "approved" | "rejected" | "served" | "cancelled";
  decision_due_at: string | null;
  decided_at: string | null;
  decided_by_user_id: number | null;
  decision_note: string;
  created_at: string;
  updated_at: string;
}

export interface SpecialFoodRequestCreateInput {
  reason: string;
  requested_date: string;
}

export interface SpecialFoodDecisionInput {
  approve: boolean;
  note?: string;
}

export interface SpecialFoodFulfillInput {
  status: "served" | "cancelled";
  note?: string;
}

export interface Registration {
  id: number;
  user_id: number;
  student_user_id: number;
  status: "pending" | "approved" | "rejected";
  submitted_at: string;
  decided_at: string | null;
  decided_by_user_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface RegistrationDecisionInput {
  approve: boolean;
  reason?: string;
}

export interface RegistrationWindow {
  id: number;
  cycle_or_period: string;
  opens_at: string;
  closes_at: string;
  is_open: boolean;
  opened_by_user_id: number;
  created_at: string;
  updated_at: string;
}

export interface RegistrationWindowCreateInput {
  cycle_or_period: string;
  opens_at: string;
  closes_at: string;
}

export interface Deregistration {
  id: number;
  user_id: number;
  student_user_id: number;
  status: "pending" | "approved_awaiting_effective_date" | "rejected";
  effective_date: string | null;
  submitted_at: string;
  decided_at: string | null;
  decided_by_user_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface DeregistrationDecisionInput {
  approve: boolean;
  reason?: string;
}

export interface RebateRequest {
  id: number;
  user_id: number;
  student_user_id: number;
  reason: "medical" | "institute_leave" | "family_function" | "other";
  explanation: string;
  start_date: string;
  end_date: string;
  status: "pending" | "approved" | "rejected";
  approved_start_date: string | null;
  approved_end_date: string | null;
  decided_at: string | null;
  decided_by_user_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface RebateRequestCreateInput {
  reason: "medical" | "institute_leave" | "family_function" | "other";
  explanation?: string;
  start_date: string;
  end_date: string;
}

export interface RebateDecisionInput {
  approve: boolean;
  approved_start_date?: string | null;
  approved_end_date?: string | null;
  reason?: string;
}

export interface MenuItem {
  id: number;
  day: string;
  meal: "breakfast" | "lunch" | "dinner";
  item: string;
  published_at: string | null;
  created_by_user_id: number;
  created_at: string;
  updated_at: string;
}

export interface MenuItemCreateInput {
  day: string;
  meal: "breakfast" | "lunch" | "dinner";
  item: string;
}

export interface MonthlyBill {
  id: number;
  user_id: number;
  student_user_id: number;
  month: string;
  state: "generated" | "finalized" | "published";
  served_day_charges: string;
  special_meal_charges: string;
  rebate_deductions: string;
  total: string;
  generated_at: string;
  finalized_at: string | null;
  published_at: string | null;
  finalized_by_user_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface Feedback {
  id: number;
  user_id: number;
  student_user_id: number;
  text: string;
  created_at: string;
  updated_at: string;
}

export interface FeedbackCreateInput {
  text: string;
}

export interface VacationSurvey {
  id: number;
  vacation: string;
  response_deadline: string;
  is_open: boolean;
  created_by_user_id: number;
  created_at: string;
  updated_at: string;
}

export interface VacationSurveyCreateInput {
  vacation: string;
  response_deadline: string;
}

export interface VacationResponse {
  id: number;
  survey: number;
  student_user_id: number;
  response: "yes" | "no" | "default_no";
  responded_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface VacationResponseCreateInput {
  response: "yes" | "no";
}

export interface SurveySummary {
  survey_id: number;
  vacation: string;
  response_deadline: string;
  is_open: boolean;
  yes: number;
  no: number;
  default_no: number;
  total: number;
}

export interface Announcement {
  id: number;
  title: string;
  body: string;
  publisher_user_id: number;
  published_at: string;
  created_at: string;
  updated_at: string;
}

export interface AnnouncementCreateInput {
  title: string;
  body: string;
}

export interface RoleAssignment {
  id: number;
  designation: "caretaker" | "warden";
  employee_user_id: number;
  effective_from: string;
  effective_until: string | null;
  is_active: boolean;
  assigned_by_user_id: number;
  created_at: string;
  updated_at: string;
}

export interface RoleAssignmentCreateInput {
  designation: "caretaker" | "warden";
  employee_user_id: number;
  effective_from: string;
  effective_until?: string | null;
}

export interface OperationalReport {
  period: string;
  total_registered_students: number;
  pending_registrations: number;
  active_rebates: number;
  pending_special_food: number;
  bills_generated: number;
  feedback_count: number;
}

export interface SupervisoryReport {
  period: string;
  total_billed_amount: string;
  total_rebate_deductions: string;
  total_special_food_charges: string;
  survey_participation_rate: number;
  feedback_count: number;
}

export interface StudentRequestsOverview {
  registrations: Registration[];
  deregistrations: Deregistration[];
  rebates: RebateRequest[];
  special_food: SpecialFoodRequest[];
}
