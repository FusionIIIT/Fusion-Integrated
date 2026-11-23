// Mirrors modules/phc/api/serializers.py.
export interface Page<T> {
  next: string | null;
  previous: string | null;
  results: T[];
}

export type DayOfWeek = 0 | 1 | 2 | 3 | 4 | 5 | 6;
export type AttendanceStatus = "available" | "departed";
export type ClaimEvent = "approve" | "forward" | "pay" | "reject" | "verify";
export type RequisitionEvent = "approve" | "fulfill" | "reject";

export interface Slot {
  day_of_week: DayOfWeek;
  day_label?: string;
  start_time: string;
  end_time: string;
}

export interface Schedule {
  id: number;
  doctor_name: string;
  specialization: string;
  is_published: boolean;
  published_at: string | null;
  slots: Slot[];
  today_status: AttendanceStatus | null;
}

export interface ScheduleInput {
  doctor_name: string;
  specialization: string;
  slots: Slot[];
}

export interface Prescription {
  id?: number;
  medicine: string;
  dosage: string;
  duration_days: number | null;
  instructions: string;
}

export interface Visit {
  id: number;
  patient_user_id: number;
  visit_date: string;
  complaint: string;
  diagnosis: string;
  prescriptions: Prescription[];
  created_at: string;
}

export interface VisitInput {
  patient_user_id: number;
  visit_date: string;
  complaint: string;
  diagnosis: string;
  prescriptions: Prescription[];
}

export interface Patient {
  user_id: number;
  display_name: string;
  kind: string;
}

export interface ClaimAction {
  event: string;
  from_status: string;
  to_status: string;
  note: string;
  created_at: string;
}

export interface Claim {
  id: number;
  user_id: number;
  prescription: number;
  prescription_label: string;
  expense_date: string;
  amount: string;
  description: string;
  status: string;
  status_label: string;
  submitted_at: string;
  actions: ClaimAction[];
  allowed_events: ClaimEvent[];
}

export interface ClaimInput {
  prescription_id: number;
  expense_date: string;
  amount: string;
  description: string;
}

export interface EligiblePrescription {
  id: number;
  medicine: string;
  dosage: string;
  visit_date: string;
}

export interface InventoryItem {
  id: number;
  name: string;
  unit: string;
  stock_level: string;
  reorder_threshold: string;
  is_low: boolean;
}

export interface InventoryItemInput {
  name: string;
  unit: string;
  stock_level: string;
  reorder_threshold: string;
}

export interface StockAdjustment {
  id: number;
  item: number;
  delta: string;
  level_after: string;
  reason: string;
  created_at: string;
  low_stock_alert: boolean;
}

export interface LowStockAlert {
  id: number;
  item: number;
  item_name: string;
  level: string;
  threshold: string;
  created_at: string;
}

export interface RequisitionLine {
  item: number;
  item_name: string;
  unit: string;
  quantity: string;
}

export interface Requisition {
  id: number;
  originator_user_id: number;
  purpose: string;
  status: string;
  status_label: string;
  lines: RequisitionLine[];
  decision_note: string;
  decided_at: string | null;
  fulfilled_at: string | null;
  created_at: string;
  allowed_events: RequisitionEvent[];
}

export interface RequisitionInput {
  purpose: string;
  lines: { item_id: number; quantity: string }[];
}

export interface AmbulanceLog {
  id: number;
  used_at: string;
  patient_name: string;
  destination: string;
  created_at: string;
}

export interface AmbulanceInput {
  used_at: string;
  patient_name: string;
  destination: string;
}

export interface Advisory {
  id: number;
  title: string;
  body: string;
  published_at: string;
}

export interface Notification {
  id: number;
  kind: string;
  message: string;
  resource_type: string;
  resource_id: number;
  created_at: string;
}

export type ReportCategory = "demographics" | "utilization" | "inventory";

export interface Report {
  category: ReportCategory;
  start: string;
  end: string;
  data: Record<string, unknown>;
}
