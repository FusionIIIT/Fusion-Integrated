export interface CoursePerson {
  user_id: number;
  name: string;
  email: string;
  department: string;
}

export interface CourseWorkspaceSummary {
  id: number;
  code: string;
  title: string;
  semester: string;
  academic_year: string;
  credits: number;
  is_published: boolean;
}

export interface CourseWorkspaceDetail {
  id: number;
  code: string;
  title: string;
  description: string;
  semester: string;
  academic_year: string;
  credits: number;
  syllabus: string;
  schedule: string;
  is_published: boolean;
  allow_ta_announcements: boolean;
  instructors: CoursePerson[];
  tas: CoursePerson[];
  viewer_role: "instructor" | "ta" | "student" | "observer" | null;
  can_manage: boolean;
}

export interface WorkspacesResponse {
  count: number;
  results: CourseWorkspaceSummary[];
}

export interface UpdateWorkspacePayload {
  title?: string;
  description?: string;
  syllabus?: string;
  schedule?: string;
  is_published?: boolean;
  allow_ta_announcements?: boolean;
}

export interface CourseAnnouncement {
  id: number;
  workspace_id: number;
  title: string;
  body: string;
  is_published: boolean;
  published_at: string | null;
  created_by_id: number;
  author_name: string;
  created_at: string;
  updated_at: string;
}

export interface AnnouncementsResponse {
  count: number;
  results: CourseAnnouncement[];
}

export interface CreateAnnouncementPayload {
  title: string;
  body: string;
  is_published?: boolean;
}

export interface UpdateAnnouncementPayload {
  title?: string;
  body?: string;
  is_published?: boolean;
}

export interface CourseMaterialSection {
  id: number;
  workspace_id: number;
  title: string;
  description: string;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface CourseMaterial {
  id: number;
  workspace_id: number;
  section: number | null;
  section_title: string | null;
  title: string;
  description: string;
  material_type: "file" | "link" | "note";
  file_url: string | null;
  filename: string;
  file_size: number;
  mime_type: string;
  link_url: string;
  content: string;
  is_published: boolean;
  release_at: string | null;
  is_available: boolean;
  is_scheduled: boolean;
  created_by_id: number;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export interface MaterialsResponse {
  count: number;
  results: CourseMaterial[];
}

export interface CreateSectionPayload {
  title: string;
  description?: string;
  sort_order?: number;
}

export interface CreateMaterialPayload {
  title: string;
  material_type: "file" | "link" | "note";
  section_id?: number | null;
  description?: string;
  link_url?: string;
  content?: string;
  is_published?: boolean;
  release_at?: string | null;
  sort_order?: number;
}

export interface UpdateMaterialPayload {
  title?: string;
  section_id?: number | null;
  clear_section?: boolean;
  description?: string;
  link_url?: string;
  content?: string;
  is_published?: boolean;
  release_at?: string | null;
  clear_release_at?: boolean;
  sort_order?: number;
}

export interface CourseAssignment {
  id: number;
  workspace_id: number;
  title: string;
  description: string;
  instructions: string;
  max_points?: number;
  due_at: string | null;
  has_passed: boolean;
  is_published: boolean;
  published_at: string | null;
  created_by_id: number;
  author_name: string;
  created_at: string;
  updated_at: string;
}

export interface AssignmentsResponse {
  count: number;
  results: CourseAssignment[];
}

export interface CreateAssignmentPayload {
  title: string;
  description?: string;
  instructions?: string;
  due_at?: string | null;
  is_published?: boolean;
}

export interface UpdateAssignmentPayload {
  title?: string;
  description?: string;
  instructions?: string;
  due_at?: string | null;
  clear_due_at?: boolean;
  is_published?: boolean;
}

export type SubmissionType = "file" | "text" | "link";
export type SubmissionStatus = "submitted" | "late";

export interface CourseSubmission {
  id: number;
  assignment_id: number;
  workspace_id: number;
  student_id: number;
  student_name: string;
  student_username: string;
  submission_type: SubmissionType;
  filename: string;
  file_size: number;
  file_url: string | null;
  link_url: string;
  content: string;
  submitted_at: string;
  is_late: boolean;
  attempt_number: number;
  status: SubmissionStatus;
  grade?: CourseGrade | null;
  created_at: string;
  updated_at: string;
}

export type GradeStatus = "draft" | "released";

export interface CourseGrade {
  id: number;
  submission_id: number;
  assignment_id: number;
  workspace_id: number;
  student_id: number;
  grader_id: number;
  grader_name: string;
  score: string;
  feedback: string;
  status: GradeStatus;
  graded_at: string;
  released_at: string | null;
  released_by_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface CourseGradeAudit {
  id: number;
  grade_id: number;
  actor_id: number;
  actor_name: string;
  action: string;
  score_before: string | null;
  score_after: string | null;
  feedback_before: string;
  feedback_after: string;
  status_before: string;
  status_after: string;
  created_at: string;
}

export interface GradeSubmissionPayload {
  score: number;
  feedback?: string;
}

export interface ReleaseGradesPayload {
  submission_id?: number | null;
}

export interface ReleaseGradesResponse {
  released_count: number;
  results: CourseGrade[];
}

export interface SubmissionsResponse {
  count: number;
  results: CourseSubmission[];
}

export interface SubmitAssignmentPayload {
  submission_type: SubmissionType;
  file?: File | null;
  content?: string;
  link_url?: string;
}

