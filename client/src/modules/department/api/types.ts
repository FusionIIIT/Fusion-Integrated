export interface Notice {
  id: number;
  message: string;
  created_at: string;
}

export interface Slot {
  id: number;
  title: string;
  kind: "class" | "lab";
  term: string;
  day: number;
  starts_at: string;
  ends_at: string;
  programme: string;
  batch_year: number;
  room: string;
  instructor_id: number;
}

export interface Lab {
  id: number;
  name: string;
  details: string;
}

export interface Proposal {
  id: number;
  field: "official_name" | "core_policies";
  value: string;
  status: string;
  decided_at: string | null;
}

export interface Item {
  id: number;
  name: string;
  quantity: number;
}

export interface StockRequest {
  id: number;
  item_name: string;
  quantity: number;
  status: string;
  created_at: string;
}

export interface Feedback {
  id: number;
  content: string;
  category: string;
  status: string;
  created_at: string;
  reviewed_at: string | null;
  disposed_at: string | null;
}

export interface ManagedAnnouncement extends Announcement {
  target_roles: string[];
  target_programmes: string[];
  target_batch_years: number[];
}

export interface Announcement {
  id: number;
  content: string;
  published_at: string;
}

export interface Details {
  department: string;
  official_name: string;
  general_information: string;
  core_policies: string;
}

export interface AcademicContext {
  programme: string;
  batch_year: number | null;
}
