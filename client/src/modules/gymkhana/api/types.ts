export interface Club {
  id: number;
  code: string;
  name: string;
  description: string;
}

export interface Application {
  id: number;
  club: Club;
  student_id: number;
  achievements: string;
  statement: string;
  status: "open" | "approved" | "rejected";
  reviewed_by: number | null;
  reviewed_at: string | null;
  review_remarks: string;
  created_at: string;
  updated_at: string;
}

export interface Results<T> {
  results: T[];
}
