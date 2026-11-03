/** LMS TypeScript Type Definitions
 * Generated via authorized local Qwen 2.5 7B coding agent.
 */

export type Role = "instructor" | "ta" | "student" | "observer";
export type MaterialType = "note" | "file" | "link";
export type SubmissionType = "file" | "text" | "link";
export type SubmissionStatus = "submitted" | "graded" | "late";

export interface Course {
  id: number;
  code: string;
  name: string;
  description?: string;
  academic_year: number;
  semester: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CourseMembership {
  id: number;
  course: number;
  user_id: number;
  role: Role;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ModuleSection {
  id: number;
  course: number;
  title: string;
  description?: string;
  order: number;
  is_published: boolean;
  created_at: string;
  updated_at: string;
}

export interface CourseMaterial {
  id: number;
  course: number;
  section?: number | null;
  title: string;
  material_type: MaterialType;
  note_content?: string;
  file_storage_key?: string;
  link_url?: string;
  is_published: boolean;
  order: number;
  created_at: string;
  updated_at: string;
}

export interface Announcement {
  id: number;
  course: number;
  title: string;
  content: string;
  author_user_id: number;
  author_role: Role;
  is_pinned: boolean;
  created_at: string;
  updated_at: string;
}

export interface Assignment {
  id: number;
  course: number;
  section?: number | null;
  title: string;
  description?: string;
  points_possible: number;
  due_date: string;
  submission_type: SubmissionType;
  is_published: boolean;
  created_at: string;
  updated_at: string;
}

export interface Submission {
  id: number;
  assignment: number;
  student_user_id: number;
  version: number;
  submission_type: SubmissionType;
  content_text?: string;
  file_storage_key?: string;
  link_url?: string;
  submitted_at: string;
  status: SubmissionStatus;
  created_at: string;
  updated_at: string;
}

export interface Grade {
  id: number;
  submission: number;
  assessor_user_id: number;
  assessor_role: Role;
  points_awarded: number;
  feedback_text?: string;
  is_draft: boolean;
  released_at?: string;
  released_by_user_id?: number;
  created_at: string;
  updated_at: string;
}

export interface GradeAuditLog {
  id: number;
  grade: number;
  assessor_user_id: number;
  assessor_role: Role;
  points_awarded: number;
  feedback_text?: string;
  is_draft: boolean;
  action: string;
  reason: string;
  changed_at: string;
}

export interface ScheduledRelease {
  id: number;
  material?: number | null;
  assignment?: number | null;
  scheduled_publish_at: string;
  processed_at?: string | null;
  is_cancelled: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateSectionPayload {
  course: number;
  title: string;
  description?: string;
  order?: number;
  is_published?: boolean;
}

export interface CreateMaterialPayload {
  course: number;
  section?: number | null;
  title: string;
  material_type: MaterialType;
  note_content?: string;
  file_storage_key?: string;
  link_url?: string;
  is_published?: boolean;
  order?: number;
  scheduled_publish_at?: string;
}

export interface CreateAssignmentPayload {
  course: number;
  section?: number | null;
  title: string;
  description?: string;
  points_possible: number;
  due_date: string;
  submission_type: SubmissionType;
  is_published?: boolean;
  scheduled_publish_at?: string;
}

export interface SubmitAssignmentPayload {
  submission_type: SubmissionType;
  content_text?: string;
  file_storage_key?: string;
  link_url?: string;
}

export interface GradePayload {
  action: "draft" | "release";
  points: number;
  feedback?: string;
  reason?: string;
  role?: string;
}

export interface CreateAnnouncementPayload {
  course: number;
  title: string;
  content: string;
  is_pinned?: boolean;
}

export interface UploadFileResponse {
  storage_key: string;
  filename: string;
  size: number;
}
