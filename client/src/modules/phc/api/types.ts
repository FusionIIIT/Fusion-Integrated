export interface Page<T> {
  results: T[];
  next: string | null;
  previous: string | null;
}

export interface Doctor {
  id: number;
  display_name: string;
  specialization: string;
  is_active: boolean;
}

export interface ScheduleSlot {
  id: number;
  doctor: Doctor;
  day_of_week: number;
  starts_at: string;
  ends_at: string;
  publication: "draft" | "published";
  attendance_status?: "available" | "departed" | null;
}

export interface Prescription {
  id: number;
  details: string;
  issued_on: string;
  issued_by_user_id: number;
  created_at: string;
}

export interface PatientVisit {
  id: number;
  patient_user_id: number;
  visited_on: string;
  notes: string;
  recorded_by_user_id: number;
  prescriptions: Prescription[];
  created_at: string;
}

export interface PatientSearchResult {
  user_id: number;
  display_name: string;
  kind: string;
}

export interface ReimbursementClaim {
  id: number;
  claimant_user_id: number;
  prescription: number;
  prescription_issued_on: string;
  prescription_details: string;
  claim_amount: string;
  expense_date: string;
  bill_reference: string;
  remarks: string;
  state: string;
  submitted_at: string;
  actions: Array<{
    from_state: string;
    to_state: string;
    event: string;
    actor_user_id: number;
    created_at: string;
  }>;
}

export interface InventoryItem {
  id: number;
  name: string;
  unit: string;
  reorder_threshold: number;
  is_active: boolean;
  stock_quantity: number;
}

export interface Requisition {
  id: number;
  originator_user_id: number;
  state: string;
  decided_by_user_id: number | null;
  fulfilled_by_user_id: number | null;
  submitted_at: string;
  lines: Array<{ item: number; item_name: string; unit: string; quantity: number }>;
}

export interface AmbulanceUsage {
  id: number;
  used_at: string;
  patient_name: string;
  destination: string;
  recorded_by_user_id: number;
}

export interface HealthAdvisory {
  id: number;
  title: string;
  body: string;
  published_at: string | null;
  published_by_user_id: number | null;
}

export interface Notification {
  id: number;
  event_type: string;
  message: string;
  target_type: string;
  target_id: number;
  created_at: string;
  read_at: string | null;
}

export interface Attendance {
  id: number;
  doctor: Doctor;
  attendance_date: string;
  status: "available" | "departed";
  updated_at: string;
}

export interface Report {
  report_type: string;
  data: Record<string, unknown>;
}
