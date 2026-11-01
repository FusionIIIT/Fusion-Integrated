export interface DoctorScheduleItem {
  id: number;
  day_of_week: string;
  start_time: string;
  end_time: string;
  room_number: string;
}

export interface DoctorAttendanceInfo {
  date: string;
  day: string;
  status: "Available" | "Departed" | "On-Leave" | "Not Scheduled";
  remarks: string;
}

export interface DoctorAvailability {
  doctor_id: number;
  doctor_name: string;
  specialization: string;
  contact_phone: string;
  is_visiting: boolean;
  weekly_schedule: DoctorScheduleItem[];
  today_attendance: DoctorAttendanceInfo;
}

export interface Doctor {
  id: number;
  name: string;
  specialization: string;
  contact_phone: string;
  email: string;
  is_visiting: boolean;
  is_active: boolean;
}

export interface Prescription {
  id: number;
  visit: number;
  patient_user_id: number;
  prescription_number: string;
  prescribed_date: string;
  medicines_prescribed: string;
  scanned_document_url: string;
  notes: string;
  doctor_name: string;
  created_at: string;
}

export interface PatientVisit {
  id: number;
  patient_user_id: number;
  doctor: number | null;
  doctor_name: string;
  visit_date: string;
  symptoms: string;
  diagnosis: string;
  notes: string;
  created_by_user_id: number;
  prescriptions: Prescription[];
  created_at: string;
}

export interface ReimbursementHistory {
  id: number;
  action: string;
  from_status: string;
  to_status: string;
  actor_user_id: number;
  actor_role: string;
  comments: string;
  created_at: string;
}

export interface ReimbursementClaim {
  id: number;
  claim_number: string;
  claimant_user_id: number;
  prescription: number;
  prescription_number: string;
  expense_date: string;
  amount_claimed: string;
  amount_approved: string | null;
  bills_document_url: string;
  status:
    | "Pending PHC Review"
    | "Pending Accounts Verification"
    | "Pending Sanction"
    | "Approved for Payment"
    | "Rejected"
    | "Reimbursed";
  remarks: string;
  created_at: string;
  updated_at: string;
  history: ReimbursementHistory[];
}

export interface InventoryItem {
  id: number;
  item_code: string;
  name: string;
  category: string;
  stock_level: number;
  reorder_threshold: number;
  unit: string;
  description: string;
  is_low_stock: boolean;
}

export interface StockAdjustment {
  id: number;
  item: number;
  item_name: string;
  adjustment_type: "ADD" | "DEDUCT";
  quantity: number;
  previous_stock: number;
  new_stock: number;
  reason: string;
  adjusted_by_user_id: number;
  created_at: string;
}

export interface RequisitionItem {
  id: number;
  item: number;
  item_name: string;
  item_code: string;
  unit: string;
  quantity_requested: number;
}

export interface ProcurementRequisition {
  id: number;
  requisition_number: string;
  originator_user_id: number;
  status: "Pending Approval" | "Approved" | "Rejected" | "Fulfilled";
  justification: string;
  approver_user_id: number | null;
  decision_at: string | null;
  decision_remarks: string;
  fulfilled_at: string | null;
  fulfilled_by_user_id: number | null;
  items: RequisitionItem[];
  created_at: string;
}

export interface AmbulanceLog {
  id: number;
  patient_name: string;
  patient_user_id: number | null;
  destination: string;
  departure_time: string;
  return_time: string | null;
  driver_name: string;
  reason: string;
  recorded_by_user_id: number;
  created_at: string;
}

export interface HealthAnnouncement {
  id: number;
  title: string;
  content: string;
  priority: "Normal" | "Urgent";
  published_date: string;
  is_active: boolean;
  published_by_user_id: number;
}

export interface PHCAuditTrail {
  id: number;
  target_type: "PATIENT_RECORD" | "INVENTORY_LEVEL" | "REIMBURSEMENT_CLAIM";
  target_id: string;
  action: string;
  details: string;
  actor_user_id: number;
  actor_username: string;
  created_at: string;
}

export interface PHCNotification {
  id: number;
  recipient_user_id: number;
  notification_type: "LOW_STOCK" | "REQUISITION_DECISION" | "REIMBURSEMENT_STATUS";
  title: string;
  message: string;
  is_read: boolean;
  created_at: string;
}
