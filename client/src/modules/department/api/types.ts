/** Wire types for the Department API. */

export interface Page<T> {
  results: T[];
  count?: number;
  next: string | null;
  previous: string | null;
}

export interface Department {
  id: number;
  code: string;
  name: string;
  description: string;
  head_user_id: number | null;
  admin_user_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface Announcement {
  id: number;
  department: number;
  title: string;
  body: string;
  academic_year: string;
  programme: string;
  role_target: string;
  is_hidden: boolean;
  created_by_user_id: number;
  created_at: string;
}

export interface InventoryItem {
  id: number;
  department: number;
  name: string;
  quantity: number;
  unit: string;
  created_at: string;
  updated_at: string;
}

export type StockRequestStatus = "pending" | "approved" | "rejected" | "issued";

export interface StockRequest {
  id: number;
  department: number;
  item: number;
  requester_user_id: number;
  quantity: number;
  status: StockRequestStatus;
  approved_by_user_id: number | null;
  issued_by_user_id: number | null;
  created_at: string;
}

export type FeedbackStatus = "submitted" | "reviewed" | "resolved" | "closed";

export interface Feedback {
  id: number;
  department: number;
  submitter_user_id: number;
  subject: string;
  body: string;
  category: string;
  status: FeedbackStatus;
  created_at: string;
}

export interface DepartmentProfile {
  id: number;
  department: number;
  user_id: number;
  display_name: string;
  kind: string;
  programme: string;
  discipline: string;
  batch_year: number | null;
  notes: string;
}

export interface Timetable {
  id: number;
  department: number;
  title: string;
  academic_year: string;
  programme: string;
  uploaded_by_user_id: number;
  created_at: string;
}

export interface TimetableSlot {
  id: number;
  timetable: number;
  day: string;
  start_time: string;
  end_time: string;
  subject: string;
  faculty_user_id: number | null;
  room: string;
}

export interface LabResource {
  id: number;
  department: number;
  name: string;
  description: string;
  quantity: number;
  updated_by_user_id: number;
  created_at: string;
}

export interface DepartmentDetail {
  id: number;
  department: number;
  name: string;
  core_policies: string;
  head_user_id: number | null;
}

export interface DepartmentDetailChange {
  id: number;
  department: number;
  field_name: string;
  proposed_value: string;
  status: "pending" | "approved" | "rejected";
  proposed_by_user_id: number;
  decided_by_user_id: number | null;
  created_at: string;
}
