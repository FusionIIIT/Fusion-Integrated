/** Wire types for the Hostel Management (HM) module API. */

export interface Page<T> {
  results: T[];
  next: string | null;
  previous: string | null;
  count?: number;
}

export type HostelGender = "boys" | "girls" | "coed";
export type RoleBindingType = "warden" | "caretaker";
export type RoomStatus = "available" | "occupied" | "full" | "maintenance" | "blocked";
export type AccommodationRequestStatus = "pending" | "approved" | "allocated" | "rejected" | "cancelled";
export type AllotmentStatus = "active" | "vacated" | "transferred";
export type AttendanceStatus = "present" | "absent" | "on_leave";
export type LeaveType = "casual" | "home" | "medical" | "academic" | "emergency";
export type LeaveStatus = "pending" | "approved" | "rejected" | "cancelled";
export type ComplaintCategory = "electrical" | "plumbing" | "carpentry" | "cleanliness" | "internet" | "discipline" | "mess" | "other";
export type ComplaintSeverity = "low" | "medium" | "high" | "emergency";
export type ComplaintStatus = "open" | "in_progress" | "resolved" | "escalated" | "closed" | "rejected";
export type GuestRoomBookingStatus = "pending" | "approved" | "rejected" | "checked_in" | "checked_out" | "cancelled";
export type ExtendedStayReason = "internship" | "project" | "exam" | "medical" | "other";
export type ExtendedStayStatus = "pending" | "approved" | "rejected" | "cancelled";
export type ComplianceStatus = "pending" | "verified" | "waived";
export type FineStatus = "pending" | "paid" | "waived";
export type InventoryCategory = "furniture" | "electrical" | "cleaning" | "bedding" | "appliance" | "sports" | "other";
export type StaffRole = "cleaner" | "electrician" | "plumber" | "security" | "mess_helper" | "attendant";
export type StaffShift = "morning" | "evening" | "night";
export type SecurityShiftType = "morning" | "evening" | "night" | "patrol";
export type NoticeAudience = "all" | "students" | "caretakers" | "wardens";

export interface Hostel {
  id: number;
  name: string;
  code: string;
  capacity: number;
  gender: HostelGender;
  description: string;
  is_active: boolean;
  rooms_count?: number;
  active_bindings_count?: number;
  created_at: string;
}

export interface HostelRoleBinding {
  id: number;
  hostel: number;
  hostel_name?: string;
  hostel_code?: string;
  user_id: number;
  user_name?: string;
  user_email?: string;
  role: RoleBindingType;
  start_date: string;
  end_date: string | null;
  is_active: boolean;
  assigned_by_user_id: number | null;
  created_at: string;
}

export interface Room {
  id: number;
  hostel: number;
  hostel_code?: string;
  hostel_name?: string;
  room_number: string;
  floor: number;
  capacity: number;
  current_occupancy: number;
  status: RoomStatus;
  status_remarks: string;
  is_available: boolean;
  created_at: string;
}

export interface AccommodationRequest {
  id: number;
  student_user_id: number;
  student_name?: string;
  student_roll_number?: string;
  preferred_hostel: number;
  preferred_hostel_name?: string;
  academic_year: string;
  semester: number;
  reason: string;
  status: AccommodationRequestStatus;
  allotted_room: number | null;
  review_notes: string;
  created_at: string;
}

export interface RoomAllotment {
  id: number;
  student_user_id: number;
  student_name?: string;
  student_roll_number?: string;
  hostel: number;
  hostel_name?: string;
  hostel_code?: string;
  room: number;
  room_number?: string;
  bed_number: string;
  allotment_date: string;
  vacated_date: string | null;
  status: AllotmentStatus;
  vacation_clearance_status: boolean;
  vacation_remarks: string;
  created_at: string;
}

export interface AttendanceRecord {
  id: number;
  student_user_id: number;
  student_name?: string;
  hostel: number;
  date: string;
  status: AttendanceStatus;
  remarks: string;
  recorded_by_user_id: number | null;
  created_at: string;
}

export interface HostelLeave {
  id: number;
  student_user_id: number;
  student_name?: string;
  hostel: number;
  hostel_name?: string;
  leave_type: LeaveType;
  from_date: string;
  to_date: string;
  reason: string;
  destination: string;
  emergency_contact: string;
  status: LeaveStatus;
  decision_by_user_id: number | null;
  decision_at: string | null;
  decision_remarks: string;
  created_at: string;
}

export interface HostelComplaint {
  id: number;
  student_user_id: number;
  student_name?: string;
  hostel: number;
  hostel_name?: string;
  title: string;
  description: string;
  location: string;
  category: ComplaintCategory;
  severity: ComplaintSeverity;
  status: ComplaintStatus;
  assigned_worker: string;
  resolution_notes: string;
  resolved_at: string | null;
  escalated_at: string | null;
  created_at: string;
}

export interface GuestRoomBooking {
  id: number;
  student_user_id: number;
  student_name?: string;
  hostel: number;
  hostel_name?: string;
  guest_name: string;
  relationship: string;
  num_guests: number;
  check_in_date: string;
  check_out_date: string;
  purpose: string;
  status: GuestRoomBookingStatus;
  allocated_room_number: string;
  charges: string | number;
  decision_remarks: string;
  created_at: string;
}

export interface ExtendedStayRequest {
  id: number;
  student_user_id: number;
  student_name?: string;
  hostel: number;
  hostel_name?: string;
  reason_type: ExtendedStayReason;
  reason_details: string;
  from_date: string;
  to_date: string;
  supporting_document_url: string;
  status: ExtendedStayStatus;
  charge_amount: string | number;
  payment_deadline: string | null;
  compliance_status: ComplianceStatus;
  decision_remarks: string;
  created_at: string;
}

export interface HostelFine {
  id: number;
  student_user_id: number;
  student_name?: string;
  hostel: number;
  hostel_name?: string;
  amount: string | number;
  reason: string;
  issued_date: string;
  due_date: string | null;
  status: FineStatus;
  receipt_reference: string;
  remarks: string;
  imposed_by_user_id: number | null;
  created_at: string;
}

export interface HostelInventory {
  id: number;
  hostel: number;
  hostel_name?: string;
  item_name: string;
  category: InventoryCategory;
  quantity_total: number;
  quantity_in_use: number;
  quantity_available: number;
  location_or_room: string;
  condition_notes: string;
  last_audited_at: string | null;
}

export interface HostelStaff {
  id: number;
  hostel: number;
  hostel_name?: string;
  name: string;
  phone: string;
  role: StaffRole;
  shift: StaffShift;
  is_active: boolean;
  remarks: string;
}

export interface SecurityShift {
  id: number;
  hostel: number;
  hostel_name?: string;
  guard_name: string;
  shift_date: string;
  shift_type: SecurityShiftType;
  checkpoint_location: string;
  contact_number: string;
  supervisor_notes: string;
}

export interface HostelNotice {
  id: number;
  hostel: number | null;
  hostel_name?: string;
  title: string;
  content: string;
  target_audience: NoticeAudience;
  is_active: boolean;
  expires_at: string | null;
  publisher_user_id: number;
  created_at: string;
}

export interface HostelNotification {
  id: number;
  recipient_user_id: number;
  title: string;
  message: string;
  event_type: string;
  link: string;
  is_read: boolean;
  created_at: string;
}

export interface DashboardStats {
  is_admin: boolean;
  hostels_count?: number;
  active_hostels_count?: number;
  total_capacity?: number;
  total_occupancy?: number;
  pending_allotment_requests?: number;
  open_complaints?: number;
  escalated_complaints?: number;
  pending_leaves?: number;
  pending_guest_bookings?: number;
  pending_extended_stays?: number;
  unpaid_fines_count?: number;
  my_allotment?: {
    id: number;
    hostel_name: string;
    hostel_code: string;
    room_number: string;
    bed_number: string;
    allotment_date: string;
    status: string;
  } | null;
  my_pending_leaves?: number;
  my_open_complaints?: number;
  my_pending_fines?: number;
}
