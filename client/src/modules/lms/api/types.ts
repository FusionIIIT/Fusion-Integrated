export type Role = "faculty" | "ta" | "student" | "observer";

export type MaterialType = "file" | "link" | "note";
export type MaterialStatus = "draft" | "scheduled" | "published";

export type SubmissionType = "file" | "text" | "link";
export type AssignmentStatus = "draft" | "scheduled" | "published";
export type SubmissionStatus = "submitted" | "late";
export type GradeStatus = "draft" | "released";

export interface Course {
  id: number;
  code: string;
  name: string;
  academic_year: string;
  semester: string;
  syllabus: string;
  schedule: string;
  allow_ta_announcements: boolean;
  allow_ta_grading: boolean;
  is_active: boolean;
  my_role?: Role | "";
  instructors: { user_id: number; is_primary: boolean }[];
  tas: { user_id: number }[];
  materials_count?: number;
  assignments_count?: number;
  announcements_count?: number;
  created_at: string;
  updated_at: string;
}

export interface CourseMembership {
  id: number;
  course: number;
  user_id: number;
  role: Role;
  is_primary_instructor: boolean;
  is_active: boolean;
  user_display_name: string;
  user_email: string;
  created_at: string;
}

export interface CourseMaterial {
  id: number;
  course: number;
  title: string;
  material_type: MaterialType;
  section: string;
  content: string;
  link_url: string;
  file_name: string;
  file_size: number;
  status: MaterialStatus;
  release_date: string | null;
  created_by_user_id: number;
  is_available: boolean;
  created_at: string;
  updated_at: string;
}

export interface CourseAnnouncement {
  id: number;
  course: number;
  title: string;
  content: string;
  posted_by_user_id: number;
  posted_by_role: string;
  posted_by_name: string;
  is_pinned: boolean;
  created_at: string;
  updated_at: string;
}

export interface GradeChangeAudit {
  id: number;
  grade: number;
  previous_points: string | number | null;
  new_points: string | number;
  previous_feedback: string;
  new_feedback: string;
  changed_by_user_id: number;
  changed_by_name: string;
  change_reason: string;
  changed_at: string;
}

export interface SubmissionGrade {
  id: number;
  submission: number;
  points_awarded: string | number;
  feedback: string;
  status: GradeStatus;
  graded_by_user_id: number;
  graded_by_role: string;
  graded_by_name: string;
  released_at: string | null;
  released_by_user_id: number | null;
  created_at: string;
  updated_at: string;
  audit_logs?: GradeChangeAudit[];
}

export interface AssignmentSubmission {
  id: number;
  assignment: number;
  assignment_title: string;
  assignment_points_possible: string | number;
  student_user_id: number;
  submission_type: SubmissionType;
  text_response: string;
  link_url: string;
  file_name: string;
  submitted_at: string;
  status: SubmissionStatus;
  version: number;
  grade?: SubmissionGrade | null;
  created_at: string;
  updated_at: string;
}

export interface Assignment {
  id: number;
  course: number;
  course_code: string;
  course_name: string;
  title: string;
  instructions: string;
  submission_type: SubmissionType;
  points_possible: string | number;
  due_date: string;
  release_date: string | null;
  status: AssignmentStatus;
  allow_late_submissions: boolean;
  created_by_user_id: number;
  is_available: boolean;
  my_submission?: AssignmentSubmission | null;
  submissions_count?: number;
  created_at: string;
  updated_at: string;
}
