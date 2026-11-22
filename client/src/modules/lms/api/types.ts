/** Wire types for the LMS module API. */

export interface CourseWorkspaceSummary {
  id: number;
  course_id: number;
  course_code: string;
  title: string;
  role: string;
}

export interface CourseWorkspaceDetail {
  id: number;
  course_id: number;
  course_code: string;
  title: string;
  syllabus: string;
  schedule_info: string;
  instructors: number[];
  teaching_assistants: number[];
}

export type MaterialType = "FILE" | "LINK" | "NOTE";
export type MaterialStatus = "DRAFT" | "SCHEDULED" | "PUBLISHED" | "ARCHIVED";

export interface CourseMaterial {
  id: number;
  course_id: number;
  title: string;
  description: string;
  material_type: MaterialType;
  content_text: string;
  external_url: string;
  file_attachment: string | null;
  section_name: string;
  sort_order: number;
  status: MaterialStatus;
  release_date: string | null;
  uploaded_by: number;
  created_at: string;
}

export interface CourseAnnouncement {
  id: number;
  course_id: number;
  title: string;
  content: string;
  author_id: number;
  author_role: string;
  created_at: string;
}

export type SubmissionType = "FILE" | "TEXT" | "LINK";
export type AssignmentStatus = "DRAFT" | "SCHEDULED" | "PUBLISHED" | "CLOSED";
export type SubmissionStatus = "SUBMITTED" | "LATE";
export type GradeStatus = "DRAFT" | "PUBLISHED";

export interface Assignment {
  id: number;
  course_id: number;
  title: string;
  instructions: string;
  points_possible: string;
  submission_type: SubmissionType;
  due_date: string;
  release_date: string | null;
  status: AssignmentStatus;
  created_by: number;
  created_at: string;
  updated_at: string;
}

export interface AssignmentSubmission {
  id: number;
  assignment: number;
  student_id: number;
  submission_type: SubmissionType;
  content_text: string;
  content_link: string;
  file_attachment: string | null;
  submitted_at: string;
  attempt_number: number;
  status: SubmissionStatus;
}

export interface SubmissionGrade {
  id: number;
  submission: number;
  points_awarded: string;
  feedback_text: string;
  status: GradeStatus;
  graded_by: number;
  graded_at: string;
  published_at: string | null;
  published_by: number | null;
}

export interface GradeChangeAudit {
  id: number;
  grade: number;
  submission_id: number;
  old_points: string;
  new_points: string;
  old_feedback: string;
  new_feedback: string;
  changed_by: number;
  changed_at: string;
  reason: string;
}
