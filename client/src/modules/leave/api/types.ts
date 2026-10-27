export interface LeaveBalance {
  id: number;
  user_id: number;
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
  category: string;
  entry_type: string;
  change_amount: string;
  balance_after: string;
  reference_id: number | null;
  remarks: string;
  created_at: string;
}

export interface SubstituteRequest {
  id: number;
  application_id: number;
  substitute_user_id: number;
  status: "pending" | "accepted" | "declined";
  responsibilities: string;
  response_remarks: string;
  responded_at: string | null;
  is_current: boolean;
  created_at: string;
}

export interface LeaveActionHistory {
  id: number;
  actor_user_id: number;
  actor_role: string;
  action: string;
  remarks: string;
  created_at: string;
}

export interface LeaveApplication {
  id: number;
  user_id: number;
  category: "CL" | "RH" | "SCL" | "EL" | "VL" | "COL";
  parent_leave_id: number | null;
  start_date: string;
  end_date: string;
  half_day_type: "full" | "first_half" | "second_half";
  days_count: string;
  purpose: string;
  address_during_leave: string;
  is_station_leave: boolean;
  station_departure_date: string | null;
  station_arrival_date: string | null;
  station_destination: string;
  status: string;
  unit_head_user_id: number | null;
  unit_head_reviewed_at: string | null;
  establishment_user_id: number | null;
  establishment_reviewed_at: string | null;
  sanctioning_authority_user_id: number | null;
  unit_head_recommended: boolean | null;
  unit_head_remarks: string;
  sanctioning_remarks: string;
  cancellation_reason: string;
  resumption_date: string | null;
  resumption_reviewed_at: string | null;
  resumption_outcome: "" | "no_adjustment" | "early_return_synchronized" | "late_return_synchronized";
  actual_days_count: string | null;
  is_offline_sanctioned: boolean;
  offline_reference_no: string;
  substitute_requests: SubstituteRequest[];
  actions: LeaveActionHistory[];
  created_at: string;
  updated_at: string;
}

export interface HolidayItem {
  id: number;
  name: string;
  date: string;
  kind: "closed" | "restricted";
  year: number;
  is_published: boolean;
}

export interface VacationPeriodItem {
  id: number;
  name: string;
  start_date: string;
  end_date: string;
  year: number;
  is_active: boolean;
}
