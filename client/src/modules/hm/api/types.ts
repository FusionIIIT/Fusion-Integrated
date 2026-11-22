export interface Hostel {
  id: number;
  name: string;
  code: string;
  is_active: boolean;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface HostelRoleBinding {
  id: number;
  hostel: number;
  user_id: number;
  role_kind: "warden" | "caretaker";
  is_active: boolean;
  valid_from: string | null;
  valid_to: string | null;
  assigned_by_user_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface Room {
  id: number;
  hostel: number;
  room_number: string;
  capacity: number;
  occupied_count: number;
  available_capacity: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AccommodationRequest {
  id: number;
  user_id: number;
  hostel: number | null;
  preferred_room_type: string;
  reason: string;
  status: "submitted" | "allotted" | "cancelled";
  created_at: string;
  updated_at: string;
}

export interface RoomAssignment {
  id: number;
  user_id: number;
  room: number;
  room_number: string;
  hostel_id: number;
  status: "active" | "vacated" | "exchanged";
  effective_from: string;
  effective_to: string | null;
  assigned_by_user_id: number | null;
  reason: string;
  created_at: string;
  updated_at: string;
}

export interface AttendanceRecord {
  id: number;
  user_id: number;
  hostel: number;
  date: string;
  is_present: boolean;
  recorded_by_user_id: number;
  remarks: string;
  created_at: string;
}

export interface LeaveRequest {
  id: number;
  user_id: number;
  hostel: number;
  start_date: string;
  end_date: string;
  reason: string;
  status: "submitted" | "approved" | "rejected" | "cancelled";
  decided_by_user_id: number | null;
  decision_remarks: string;
  created_at: string;
  updated_at: string;
}

export interface ComplaintEvent {
  id: number;
  actor_user_id: number;
  actor_kind: string;
  event: string;
  remarks: string;
  created_at: string;
}

export interface Complaint {
  id: number;
  user_id: number;
  hostel: number;
  category: string;
  description: string;
  status: "submitted" | "updated" | "escalated" | "resolved";
  events: ComplaintEvent[];
  created_at: string;
  updated_at: string;
}

export interface GuestBooking {
  id: number;
  user_id: number;
  hostel: number;
  guest_name: string;
  relation: string;
  start_date: string;
  end_date: string;
  status: "submitted" | "approved" | "rejected" | "cancelled";
  decided_by_user_id: number | null;
  remarks: string;
  created_at: string;
  updated_at: string;
}

export interface ExtendedStayRequest {
  id: number;
  user_id: number;
  hostel: number;
  start_date: string;
  end_date: string;
  reason: string;
  status: "submitted" | "approved" | "rejected" | "cancelled";
  decided_by_user_id: number | null;
  remarks: string;
  created_at: string;
  updated_at: string;
}

export interface FineRecord {
  id: number;
  user_id: number;
  hostel: number;
  amount: string;
  reason: string;
  imposed_by_user_id: number;
  created_at: string;
}

export interface InventoryItem {
  id: number;
  hostel: number;
  name: string;
  quantity: number;
  description: string;
  updated_by_user_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface GuardShift {
  id: number;
  hostel: number;
  guard_name: string;
  shift_date: string;
  shift_type: string;
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface Notice {
  id: number;
  hostel: number;
  title: string;
  content: string;
  status: "draft" | "published" | "withdrawn";
  published_by_user_id: number | null;
  published_at: string | null;
  created_at: string;
  updated_at: string;
}
