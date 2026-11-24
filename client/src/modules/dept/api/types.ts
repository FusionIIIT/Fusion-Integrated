/** Wire types for the Department module. */

export interface DepartmentInfo {
  code: string;
  name: string;
  description: string;
  core_policies: string;
  head_of_department_id: string | null;
  department_admin_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface Announcement {
  id: string;
  department: string;
  title: string;
  content: string;
  author_id: string;
  author_role: string;
  target_role: string;
  target_program: string;
  target_academic_year: number | null;
  status: "ACTIVE" | "HIDDEN" | "DELETED";
  created_at: string;
  updated_at: string;
}

export interface InventoryItem {
  id: string;
  department: string;
  item_code: string;
  name: string;
  category: "EQUIPMENT" | "CONSUMABLE" | "FURNITURE" | "OTHER";
  quantity: number;
  unit: string;
  created_at: string;
  updated_at: string;
}

export interface StockTransaction {
  id: string;
  inventory_item: string;
  transaction_type: "INSERTION" | "ISSUANCE" | "ADJUSTMENT";
  quantity_delta: number;
  balance_after: number;
  performed_by_id: string;
  related_request_id?: string | null;
  notes: string;
  created_at: string;
}

export interface StockRequest {
  id: string;
  department: string;
  inventory_item: string;
  item_name?: string;
  item_code?: string;
  requested_by_id: string;
  requested_quantity: number;
  purpose: string;
  status: "SUBMITTED" | "APPROVED" | "REJECTED" | "ISSUED";
  hod_decision_by_id: string | null;
  hod_decision_at: string | null;
  hod_remarks: string;
  issued_by_id: string | null;
  issued_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Feedback {
  id: string;
  department: string;
  submitted_by_id: string;
  submitter_role: string;
  category: "ACADEMIC" | "INFRASTRUCTURE" | "ADMINISTRATIVE" | "OTHER";
  title: string;
  description: string;
  status: "NEW" | "UNDER_REVIEW" | "RESOLVED" | "CLOSED";
  admin_remarks: string;
  reviewed_by_admin_id: string | null;
  reviewed_at: string | null;
  terminal_by_id: string | null;
  terminal_by_role: string | null;
  terminal_remarks: string;
  terminal_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TimetableEntry {
  id: string;
  department: string;
  program: string;
  academic_year: number;
  semester: number;
  day_of_week: number;
  day_name?: string;
  start_time: string;
  end_time: string;
  course_code: string;
  course_name: string;
  instructor_id: string;
  room_or_lab: string;
  created_at: string;
  updated_at: string;
}

export interface LabResource {
  id: string;
  department: string;
  lab_name: string;
  location: string;
  description: string;
  equipment_details: Array<Record<string, unknown>>;
  in_charge_id: string;
  created_at: string;
  updated_at: string;
}

export interface UserProfileExtension {
  id: string;
  department_code: string;
  user_id: string;
  profile_type: "STUDENT" | "FACULTY" | "ALUMNI";
  office_room: string;
  research_interests: string;
  contact_phone: string | null;
  emergency_contact: string | null;
  courses_taught: string[];
  batch_or_roll: string;
  graduation_year: number | null;
}

export interface OfficialDetailChangeRequest {
  id: string;
  department: string;
  proposed_by_id: string;
  field_name: string;
  old_value: string;
  new_value: string;
  justification: string;
  status: "PENDING" | "APPROVED" | "REJECTED";
  reviewed_by_id: string | null;
  review_reason: string;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface DepartmentRoleAssignment {
  id: string;
  department: string;
  role_name: "HOD" | "DEPT_ADMIN";
  user_id: string;
  start_date: string;
  end_date: string;
  status: "SCHEDULED" | "ACTIVE" | "REVOKED" | "EXPIRED";
  assigned_by_id: string;
  created_at: string;
  updated_at: string;
}
