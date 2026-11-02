export interface Page<T> { results: T[] }

export interface Announcement {
  id: number;
  title: string;
  body: string;
  target_roles: string[];
  target_programmes: string[];
  target_academic_years: string[];
  status: "active" | "hidden" | "deleted";
  created_at: string;
}

export interface InventoryItem {
  id: number;
  name: string;
  description: string;
  quantity: number;
  updated_at: string;
}

export interface StockRequest {
  id: number;
  item: number;
  item_name: string;
  faculty_user_id: number;
  quantity: number;
  status: "pending_hod_approval" | "approved_for_issuance" | "rejected" | "issued";
  decision_note: string;
  created_at: string;
}

export interface StockMovement {
  id: number;
  item_name: string;
  movement: "insertion" | "issue";
  quantity: number;
  actor_user_id: number;
  created_at: string;
}

export interface Feedback {
  id: number;
  submitter_user_id: number;
  body: string;
  category: string;
  status: "new" | "under_review" | "resolved" | "closed";
  initial_reviewed_by_user_id: number | null;
  initial_reviewed_at: string | null;
  handled_by_user_id: number | null;
  created_at: string;
}

export interface ResourceProfile {
  id: number;
  name: string;
  description: string;
  location: string;
  equipment: string[];
  updated_at: string;
}

export interface TimetableEntry {
  id: number;
  programme: string;
  academic_year: string;
  course: string;
  day: number;
  starts_at: string;
  ends_at: string;
  room: string;
  updated_at: string;
}

export interface DepartmentChange {
  id: number;
  field_name: string;
  proposed_value: unknown;
  status: "pending_hod_approval" | "approved" | "rejected";
  proposed_by_user_id: number;
  decision_note: string;
  created_at: string;
}

export interface DepartmentDetails {
  general: Record<string, unknown>;
  official: Record<string, unknown>;
  changes: DepartmentChange[];
}
