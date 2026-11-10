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
