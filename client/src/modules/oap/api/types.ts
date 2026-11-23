export interface Page<T> {
  results: T[];
  next: string | null;
  previous: string | null;
}

export interface Leave {
  id: number;
  status: string;
  reason: string;
  from_date: string;
  to_date: string;
  supporting_document_link: string;
  decided_at: string | null;
  created_at: string;
}

export interface LeaveInput {
  reason: string;
  from_date: string;
  to_date: string;
  supporting_document_link?: string;
}

export interface Bonafide {
  id: number;
  status: string;
  purpose: string;
  verified_at: string | null;
  decided_at: string | null;
  created_at: string;
}

export interface NoDuesCase {
  id: number;
  finalized: boolean;
  status: string;
  results: Record<string, string>;
}

export interface Verification {
  role: string;
  verified_at: string;
}

export interface Claim {
  id: number;
  status: string;
  thesis_supervisor_user_id: number;
  ta_supervisor_user_id: number;
  verifications: Verification[];
  created_at: string;
}

export interface ThesisAssignment {
  id: number;
  student_user_id: number;
  supervisor_user_id: number;
  assigned_at: string;
  superseded_at: string | null;
}

export interface TAAssignment {
  id: number;
  student_user_id: number;
  course_code: string;
  supervisor_user_id: number | null;
  assigned_at: string;
}

export interface SeminarRequest {
  id: number;
  status: string;
  created_at: string;
}

export interface SeminarSchedule {
  id: number;
  request_id: number;
  scheduled_for: string;
  venue: string;
  scheduled_at: string;
}

export interface Notice {
  id: number;
  subject: string;
  body: string;
  status: string;
  created_at: string;
}
