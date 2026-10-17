export type LeaveCategory = "CL" | "RH" | "SCL" | "EL" | "COL" | "VL";
export type HalfDay = "" | "first" | "second";
export type LeaveStatus =
  | "pending" | "recommended" | "not_recommended"
  | "approved" | "rejected" | "withdrawn";

export const CATEGORY_LABELS: Record<LeaveCategory, string> = {
  CL: "Casual Leave",
  RH: "Restricted Holiday",
  SCL: "Special Casual Leave",
  EL: "Earned Leave",
  COL: "Commuted Leave",
  VL: "Vacation Leave",
};

export interface LeaveHistory {
  from_status: string;
  to_status: string;
  actor_user_id: number;
  remarks: string;
  at: string;
}

export interface LeaveRequest {
  id: number;
  applicant_user_id: number;
  category: LeaveCategory;
  start_date: string;
  end_date: string;
  half: HalfDay;
  days: string;
  reason: string;
  status: LeaveStatus;
  is_station_leave: boolean;
  station_address: string;
  station_contact: string;
  created_at: string;
  allowed_transitions: LeaveStatus[];
  history: LeaveHistory[];
}

export interface LeaveApplication {
  category: LeaveCategory;
  start_date: string;
  end_date: string;
  half: HalfDay;
  reason: string;
  is_station_leave: boolean;
  station_address: string;
  station_contact: string;
}

export interface LeaveBalance {
  category: LeaveCategory;
  credited: string;
  availed: string;
  reserved: string;
  available: string;
}

export interface Page<T> {
  results: T[];
  next: string | null;
  previous: string | null;
}
