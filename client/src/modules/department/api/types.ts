export interface Page<T> {
  results: T[];
  count?: number;
  next?: string | null;
  previous?: string | null;
}

export interface SeminarSchedulingHistory {
  id: number;
  seminar_id: number;
  action: string;
  details: string;
  recorded_by_id: number;
  recorded_by_name: string;
  created_at: string;
}

export interface GraduateSeminar {
  id: number;
  request_id: number;
  title: string;
  speaker_id: number;
  speaker_name: string;
  scheduled_date: string;
  start_time: string;
  end_time: string;
  venue: string;
  session_chair: string;
  remarks: string;
  scheduled_by_id: number;
  scheduled_by_name: string;
  created_at: string;
  history_logs?: SeminarSchedulingHistory[];
}

export interface SeminarRequest {
  id: number;
  student_id: number;
  student_name: string;
  programme: string;
  department: string;
  topic: string;
  abstract: string;
  preferred_date?: string | null;
  faculty_advisor_id?: number | null;
  faculty_advisor_name: string;
  status: "AWAITING_SCHEDULING" | "SCHEDULED" | "REJECTED" | "CANCELLED";
  rejection_reason?: string;
  seminar?: GraduateSeminar | null;
  created_at: string;
  updated_at: string;
}

export interface SubmitSeminarRequestInput {
  topic: string;
  abstract: string;
  programme?: string;
  department?: string;
  preferred_date?: string | null;
  faculty_advisor_id?: number | null;
  faculty_advisor_name?: string;
}

export interface ScheduleSeminarInput {
  scheduled_date: string;
  start_time: string;
  end_time: string;
  venue: string;
  session_chair?: string;
  remarks?: string;
}

export interface ThesisSupervisorAllocation {
  id: number;
  student_id: number;
  student_name: string;
  programme: string;
  department: string;
  supervisor_id: number;
  supervisor_name: string;
  co_supervisor_name: string;
  thesis_topic: string;
  academic_year: string;
  status: string;
  created_at: string;
}

export interface TAAllocation {
  id: number;
  student_id: number;
  student_name: string;
  programme: string;
  department: string;
  course_code: string;
  course_name: string;
  faculty_id?: number | null;
  faculty_name: string;
  semester: string;
  academic_year: string;
  hours_per_week: number;
  created_at: string;
}

export interface DepartmentAnnouncement {
  id: number;
  title: string;
  content: string;
  department: string;
  target_audience: string;
  posted_by_id: number;
  posted_by_name: string;
  is_pinned: boolean;
  created_at: string;
}
