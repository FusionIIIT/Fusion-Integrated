// Mirrors modules/department/api/serializers.py.
export interface Page<T> {
  results: T[];
  next: string | null;
  previous: string | null;
}

export interface Headship {
  user_id: number;
  display_name: string;
}

export interface Department {
  id: number;
  code: string;
  name: string;
  core_policies: string;
  description: string;
  contact_email: string;
  contact_phone: string;
  office_location: string;
  website: string;
  headship: Headship | null;
  programmes: string[];
}

export type GeneralUpdate = Partial<Pick<Department,
  "description" | "contact_email" | "contact_phone" | "office_location" | "website">>;

export interface OfficialChange {
  id: number;
  department: string;
  field: "name" | "core_policies";
  proposed_value: string;
  previous_value: string;
  status: "pending" | "approved" | "rejected";
  proposed_by: number;
  decided_by: number | null;
  decided_at: string | null;
  reason: string;
  created_at: string;
}

export type AudienceRole = "student" | "faculty" | "dept_admin" | "hod" | "all";

export interface Announcement {
  id: number;
  department: string;
  title: string;
  body: string;
  audience_role: AudienceRole;
  programme: string;
  batch_year: number | null;
  status: "active" | "hidden" | "deleted";
  author_id: number;
  published_at: string;
  edited_at: string | null;
}

export interface AnnouncementInput {
  title: string;
  body: string;
  audience_role: AudienceRole;
  programme?: string;
  batch_year?: number | null;
}

export interface InventoryItem {
  id: number;
  name: string;
  unit: string;
  current_quantity: number;
  updated_at: string;
}

export interface StockMovement {
  id: number;
  item: number;
  item_name: string;
  kind: "receipt" | "issue";
  quantity: number;
  actor_id: number;
  stock_request: number | null;
  note: string;
  created_at: string;
}

export type StockStatus = "pending_hod" | "approved" | "rejected" | "issued";

export interface StockRequest {
  id: number;
  item: number;
  item_name: string;
  unit: string;
  requester_id: number;
  quantity: number;
  purpose: string;
  status: StockStatus;
  decided_by: number | null;
  decided_at: string | null;
  reason: string;
  issued_by: number | null;
  issued_at: string | null;
  created_at: string;
}

export type FeedbackStatus = "new" | "under_review" | "resolved" | "closed";
export const FEEDBACK_CATEGORIES = [
  "academic", "infrastructure", "administrative", "facilities", "other",
] as const;

export interface FeedbackNote {
  id: number;
  author_id: number;
  body: string;
  created_at: string;
}

export type FeedbackCategory = (typeof FEEDBACK_CATEGORIES)[number];

export interface Feedback {
  id: number;
  subject: string;
  body: string;
  category: FeedbackCategory | "";
  status: FeedbackStatus;
  submitter_id: number;
  submitter_kind: string;
  reviewed_at: string | null;
  disposed_at: string | null;
  resolution_note: string;
  created_at: string;
  notes: FeedbackNote[];
}

export interface TimetableSlotInput {
  kind: "class" | "lab";
  programme?: string;
  batch_year?: number | null;
  course_code: string;
  day_of_week: number;
  starts_at: string;
  ends_at: string;
  room?: string;
  instructor_user_id?: number | null;
}

export interface TimetableSlot extends Required<TimetableSlotInput> {
  id: number;
  updated_at: string;
}

export interface LabResource {
  id: number;
  name: string;
  location: string;
  equipment: string;
  capacity: number | null;
  status: "available" | "maintenance" | "retired";
  updated_at: string;
}

export type LabInput = Partial<Omit<LabResource, "id" | "updated_at">>;

export interface Profile {
  tier: "basic" | "limited" | "detailed" | "full";
  id: number;
  kind: "faculty" | "student" | "alumni";
  display_name: string;
  programme: string;
  department: string;
  email?: string;
  office?: string;
  research_interests?: string;
  current_position?: string;
  user_id?: number | null;
  username?: string;
  discipline?: string;
  batch_year?: number | null;
  bio?: string;
  graduation_year?: number | null;
  is_active?: boolean;
}

export interface ProfileInput {
  kind: Profile["kind"];
  user_id?: number | null;
  display_name?: string;
  office?: string;
  research_interests?: string;
  bio?: string;
  current_position?: string;
  graduation_year?: number | null;
}

export interface Tenure {
  id: number;
  department: string;
  role: "hod" | "dept_admin";
  user_id: number;
  valid_from: string;
  valid_to: string;
  assigned_by: number;
  transition_applied_at: string | null;
  in_effect: boolean;
}

export interface TenureInput {
  department: string;
  role: Tenure["role"];
  user_id: number;
  valid_from: string;
  valid_to: string;
}

export interface RoleWarning {
  department: string;
  role: Tenure["role"];
  problem: "vacant" | "ending";
  message: string;
}
