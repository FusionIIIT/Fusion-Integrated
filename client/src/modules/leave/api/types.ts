/** Wire types for the leave API. */

export interface Page<T> {
  results: T[];
  next: string | null;
  previous: string | null;
}

export interface LeaveBalance {
  id: number;
  user_id: number;
  year: string;
  category: string;
  entitled: string;
  used: string;
  available: string;
}

export interface RequestAction {
  id: number;
  actor_user_id: number;
  action: string;
  from_status: string;
  to_status: string;
  note: string;
  created_at: string;
}

export interface LeaveRequest {
  id: number;
  user_id: number;
  category: string;
  start_date: string;
  end_date: string;
  is_half_day: boolean;
  half_session: string;
  days: string;
  purpose: string;
  station_leave: boolean;
  station_address: string;
  substitute_user_id: number | null;
  substitute_status: string;
  unit: number | null;
  status: string;
  recommendation: string;
  decision_note: string;
  is_offline: boolean;
  created_at: string;
  actions: RequestAction[];
}

export interface Holiday {
  id: number;
  date: string;
  name: string;
  is_restricted: boolean;
  is_published: boolean;
}
