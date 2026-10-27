export type LeaveCategory = "CL" | "RH" | "SCL" | "EL" | "VL" | "COL";

export type LeaveStatus =
  | "draft"
  | "substitute_pending"
  | "substitute_declined"
  | "under_review"
  | "establishment_review"
  | "sanction_review"
  | "approved"
  | "rejected"
  | "withdrawn"
  | "cancel_requested"
  | "cancelled"
  | "extension_requested"
  | "resumption_submitted"
  | "closed";

export interface LeaveApplication {
  id: number;
  user_id: number;
  category: LeaveCategory;
  start_date: string;
  end_date: string;
  half_day_type: "full" | "first_half" | "second_half";
  days_count: string;
  purpose: string;
  address_during_leave?: string;
  is_station_leave: boolean;
  station_departure_date?: string;
  station_arrival_date?: string;
  station_destination?: string;
  status: LeaveStatus;
  created_at: string;
  updated_at: string;
  unit_head_recommended?: boolean;
  unit_head_remarks?: string;
  establishment_remarks?: string;
  sanctioning_remarks?: string;
}

export interface LeaveBalance {
  id: number;
  year: number;
  is_faculty: boolean;
  cl_balance: string;
  rh_balance: string;
  scl_balance: string;
  el_balance: string;
  vl_balance: string;
  col_balance: string;
}

export interface LeaveLedgerEntry {
  id: number;
  category: LeaveCategory;
  entry_type: "credit" | "debit" | "reversal" | "conversion" | "lapse" | "adjustment";
  change_amount: string;
  balance_after: string;
  reference_id?: number;
  remarks?: string;
  created_at: string;
}

export interface SubstituteRequest {
  id: number;
  application_id: number;
  substitute_user_id: number;
  status: "pending" | "accepted" | "declined";
  responsibilities: string;
  remarks?: string;
  responded_at?: string;
  created_at: string;
}

export interface HolidayCalendar {
  id: number;
  year: number;
  date: string;
  kind: "closed" | "restricted";
  title: string;
  is_published: boolean;
}

export interface VacationPeriod {
  id: number;
  year: number;
  name: string;
  start_date: string;
  end_date: string;
  is_active: boolean;
}