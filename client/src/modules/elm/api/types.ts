export interface LeaveApplication {
  id: number;
  user_id: number;
  category: string;
  start_date: string;
  end_date: string;
  half: string;
  purpose: string;
  station_leave: unknown;
  substitute_user_id: number | null;
  substitute_status: string;
  status: string;
  chargeable_days: string;
  decided_by_user_id: number | null;
  decided_at: string | null;
  decision_note: string;
  created_at: string;
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

export interface Page<T> {
  results: T[];
}

export const CATEGORY_LABELS: Record<string, string> = {
  cl: "Casual Leave", rh: "Restricted Holiday", scl: "Special Casual Leave",
  el: "Earned Leave", col: "Commuted Leave", vl: "Vacation Leave",
};
