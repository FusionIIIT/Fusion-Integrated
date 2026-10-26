export interface LeaveApplication {
  id: number;
  user_id: number;
  department: string;
  category: string;
  start_date: string;
  end_date: string;
  half: string;
  purpose: string;
  station_leave: {
    station_start?: string;
    station_end?: string;
    address?: string;
    contact?: string;
  } | null;
  substitute_user_id: number | null;
  substitute_status: string;
  status: string;
  chargeable_days: string;
  recommended_by_user_id: number | null;
  recommended_at: string | null;
  recommendation: string;
  recommendation_note: string;
  decided_by_user_id: number | null;
  decided_at: string | null;
  decision_note: string;
  actual_resumption_date: string | null;
  resumption_note: string;
  is_offline_record: boolean;
  offline_sanction_reference: string;
  created_at: string;
  updated_at?: string;
}

export interface LeaveBalance {
  category: string;
  entitled: string;
  used: string;
  available: string;
}

export interface Holiday {
  id: number;
  date: string;
  kind: string;
  label: string;
  is_published: boolean;
}

export interface VacationPeriod {
  id: number;
  name: string;
  start_date: string;
  end_date: string;
  is_active: boolean;
}

export interface Page<T> {
  results: T[];
}

export const CATEGORY_LABELS: Record<string, string> = {
  cl: "Casual Leave",
  rh: "Restricted Holiday",
  scl: "Special Casual Leave",
  el: "Earned Leave",
  col: "Commuted Leave",
  vl: "Vacation Leave",
};

export const STATUS_LABELS: Record<string, string> = {
  submitted: "Submitted",
  forwarded: "Forwarded / Recommended",
  approved: "Approved",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
  cancel_req: "Cancellation Requested",
  cancelled: "Cancelled",
  res_req: "Resumption Requested",
  resumed: "Duty Resumed",
};
