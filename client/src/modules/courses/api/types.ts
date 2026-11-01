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
