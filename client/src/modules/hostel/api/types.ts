/** TypeScript type definitions for the Hostel Management module. */

export interface Hostel {
  id: number;
  name: string;
  code: string;
  gender_policy: "boys" | "girls" | "coed";
  capacity: number;
  is_active: boolean;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface HostelRoleBinding {
  id: number;
  hostel: number;
  hostel_name: string;
  hostel_code: string;
  user_id: number;
  role: "warden" | "caretaker";
  is_active: boolean;
  start_date: string | null;
  end_date: string | null;
  assigned_by_user_id: number | null;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface Room {
  id: number;
  hostel: number;
  hostel_name: string;
  hostel_code: string;
  room_number: string;
  floor: number;
  capacity: number;
  current_occupancy: number;
  available_beds: number;
  room_type: "single" | "double" | "triple" | "guest";
  is_available: boolean;
  created_at: string;
  updated_at: string;
}

export interface AccommodationRequest {
  id: number;
  student_user_id: number;
  student_roll_number: string;
  student_name: string;
  academic_year: string;
  semester: string;
  requested_hostel: number | null;
  requested_hostel_name?: string;
  reason: string;
  status: "submitted" | "allotted" | "rejected" | "cancelled";
  created_at: string;
  updated_at: string;
}

export interface RoomAllotment {
  id: number;
  room: number;
  room_number: string;
  hostel: number;
  hostel_name: string;
  hostel_code: string;
  student_user_id: number;
  student_roll_number: string;
  student_name: string;
  allotted_at: string;
  allotted_by_user_id: number;
  is_active: boolean;
  vacated_at: string | null;
  vacation_reason: string;
}

export interface RoomAssignmentHistory {
  id: number;
  student_user_id: number;
  student_roll_number: string;
  from_room: number | null;
  from_room_number?: string;
  to_room: number | null;
  to_room_number?: string;
  action_type: string;
  performed_by_user_id: number;
  timestamp: string;
  reason: string;
}

export interface AttendanceRecord {
  id: number;
  hostel: number;
  hostel_name: string;
  student_user_id: number;
  student_roll_number: string;
  student_name: string;
  date: string;
  status: "present" | "absent" | "on_leave";
  marked_by_user_id: number;
  remarks: string;
  created_at: string;
}

export interface LeaveRequest {
  id: number;
  hostel: number;
  hostel_name: string;
  student_user_id: number;
  student_roll_number: string;
  student_name: string;
  leave_type: "home" | "academic" | "medical" | "emergency";
  start_date: string;
  end_date: string;
  reason: string;
  address_during_leave: string;
  emergency_contact: string;
  supporting_document: string;
  status: "submitted" | "approved" | "rejected";
  decision_by_user_id: number | null;
  decision_at: string | null;
  decision_remarks: string;
  created_at: string;
  updated_at: string;
}

export interface HostelComplaint {
  id: number;
  hostel: number;
  hostel_name: string;
  student_user_id: number;
  student_roll_number: string;
  student_name: string;
  room_number: string;
  category: "electrical" | "plumbing" | "carpentry" | "cleanliness" | "internet" | "discipline" | "other";
  title: string;
  description: string;
  attachment_url: string;
  status: "submitted" | "in_progress" | "resolved" | "escalated";
  action_taken: string;
  caretaker_user_id: number | null;
  resolved_at: string | null;
  escalated_to_warden: boolean;
  escalated_at: string | null;
  escalation_reason: string;
  created_at: string;
  updated_at: string;
}

export interface GuestRoomBooking {
  id: number;
  hostel: number;
  hostel_name: string;
  student_user_id: number;
  student_roll_number: string;
  student_name: string;
  guest_name: string;
  guest_relation: string;
  guest_gender: string;
  check_in_date: string;
  check_out_date: string;
  number_of_guests: number;
  assigned_room: number | null;
  assigned_room_number?: string;
  reason: string;
  status: "requested" | "approved" | "rejected" | "cancelled";
  decision_by_user_id: number | null;
  decision_at: string | null;
  decision_remarks: string;
  created_at: string;
}

export interface ExtendedStayRequest {
  id: number;
  hostel: number;
  hostel_name: string;
  student_user_id: number;
  student_roll_number: string;
  student_name: string;
  stay_reason: "internship" | "project" | "academic" | "sports" | "other";
  start_date: string;
  end_date: string;
  remarks: string;
  charge_amount: string | number;
  payment_deadline: string | null;
  payment_status: "pending" | "compliant" | "non_compliant" | "waived";
  status: "submitted" | "approved" | "rejected";
  decision_by_user_id: number | null;
  decision_at: string | null;
  decision_remarks: string;
  created_at: string;
  updated_at: string;
}

export interface HostelFine {
  id: number;
  hostel: number;
  hostel_name: string;
  student_user_id: number;
  student_roll_number: string;
  student_name: string;
  reason: string;
  amount: string | number;
  date: string;
  fine_type: "damage" | "rule_violation" | "indiscipline" | "noise" | "cleanliness" | "other";
  is_paid: boolean;
  imposed_by_user_id: number;
  created_at: string;
}

export interface HostelInventoryItem {
  id: number;
  hostel: number;
  hostel_name: string;
  item_name: string;
  category: "furniture" | "electrical" | "cleaning" | "sports" | "linen" | "other";
  total_quantity: number;
  in_use_quantity: number;
  available_quantity: number;
  condition: "good" | "fair" | "needs_repair";
  location: string;
  last_updated_by_user_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface InventoryAuditLog {
  id: number;
  item: number;
  item_name?: string;
  action: string;
  details: string;
  performed_by_user_id: number;
  timestamp: string;
}

export interface StaffAssignment {
  id: number;
  hostel: number;
  hostel_name: string;
  staff_name: string;
  role_designation: string;
  shift: "morning" | "evening" | "night" | "general";
  contact_number: string;
  duty_location: string;
  is_active: boolean;
  assigned_by_user_id: number;
  created_at: string;
}

export interface SecurityGuardShift {
  id: number;
  hostel: number;
  hostel_name: string;
  guard_name: string;
  agency_or_badge_number: string;
  shift_type: "morning" | "evening" | "night";
  shift_date: string;
  gate_or_post: string;
  contact_number: string;
  supervisor_name: string;
  is_verified: boolean;
  created_by_user_id: number;
  created_at: string;
  updated_at: string;
}

export interface HostelNotice {
  id: number;
  hostel: number | null;
  hostel_name?: string;
  title: string;
  body: string;
  category: "general" | "maintenance" | "discipline" | "event" | "emergency";
  is_pinned: boolean;
  published_by_user_id: number;
  published_by_role: string;
  is_active: boolean;
  created_at: string;
}

export interface NotificationRecord {
  id: number;
  recipient_user_id: number;
  event_type: string;
  title: string;
  message: string;
  reference_id: string;
  is_read: boolean;
  created_at: string;
}

export interface OperationalReport {
  report_type: string;
  summary?: Record<string, any>;
  hostels?: any[];
  by_category?: any[];
  by_type?: any[];
  total_hostels?: number;
  total_capacity?: number;
  total_occupancy?: number;
  occupancy_rate?: number;
  active_complaints?: number;
  pending_leaves?: number;
  active_residents?: number;
}
