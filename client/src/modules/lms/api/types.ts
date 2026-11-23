export interface Page<T> { results: T[]; next: string | null; previous: string | null }
export type ContentKind = "FILE" | "TEXT" | "LINK";
export interface Section { id: number; workspace_id: number; kind: "MODULE" | "WEEK"; label: string; order: number }
export interface Course {
  id: number; external_offering_key: string; course_code: string; course_name: string;
  working_year: string | null; session: string | null; syllabus: string; schedule: string;
  details_published_at: string | null; acting_course_role: "STUDENT" | "FACULTY" | "TA" | "OBSERVER";
  can_post_announcements: boolean;
  staff: { user_id: number; display_name: string; email: string; course_role: string }[];
  sections: Section[];
}
export interface PrivateFile { name: string; mime_type: string; size: number; sha256: string }
export interface Material {
  id: number; workspace_id: number; section_id: number | null; title: string;
  kind: "FILE" | "NOTE" | "LINK"; text: string; url: string; file: PrivateFile | null;
  order: number; state: "DRAFT" | "SCHEDULED" | "PUBLISHED"; release_at: string | null;
  published_at: string | null; author_user_id: number;
}
export interface Assignment {
  id: number; workspace_id: number; title: string; instructions: string; due_at: string;
  submission_type: ContentKind; points_possible: string;
  state: "DRAFT" | "SCHEDULED" | "AVAILABLE"; release_at: string | null;
  published_at: string | null; author_user_id: number;
}
export interface Announcement { id: number; workspace_id: number; content: string; created_at: string; author_user_id: number }
export interface Submission {
  id: number; assignment_id: number; user_id: number; kind: ContentKind;
  text: string; url: string; file: PrivateFile | null; submitted_at: string; policy_version: string;
}
export interface Grade {
  id: number; submission_id: number; assignment_id: number; user_id: number; points: string;
  feedback: string; state: "DRAFT" | "RELEASED"; grader_user_id: number; graded_at: string;
  released_by_user_id: number | null; released_at: string | null;
}
export interface Policy {
  id: number | null; workspace_id: number; version: number; effective_from: string | null;
  can_ta_post_announcements: boolean; decision_version: string; author_user_id: number | null;
}
export interface CourseInput { syllabus?: string; schedule?: string }
export interface PolicyInput { can_ta_post_announcements: boolean }
export interface SectionInput { kind: Section["kind"]; label: string; order?: number }
export interface ReleaseInput { release_at?: string | null }
export interface AssignmentInput {
  title?: string; instructions: string; due_at: string; submission_type: ContentKind; points_possible: string;
}
export interface GradeInput { points: string; feedback?: string }
