export interface CourseWorkspace {
  course_id: number;
  title: string;
}

export interface CourseMaterial {
  id: number;
  course_id: number;
  title: string;
  material_type: "file" | "link" | "note";
  content: string;
  section: string;
  status: "draft" | "published" | "scheduled";
  release_at: string | null;
  user_id: number;
  created_at: string;
}

export interface Announcement {
  id: number;
  course_id: number;
  user_id: number;
  content: string;
  is_pinned: boolean;
  created_at: string;
}

export interface Assignment {
  id: number;
  course_id: number;
  title: string;
  instructions: string;
  due_at: string;
  submission_type: "file" | "text" | "link";
  points_possible: number;
  status: "draft" | "published" | "scheduled" | "available";
  release_at: string | null;
  max_attempts: number;
  user_id: number;
  created_at: string;
}

export interface Submission {
  id: number;
  assignment: number;
  user_id: number;
  submission_type: "file" | "text" | "link";
  content: string;
  file: string | null;
  submitted_at: string;
  status: "submitted" | "late" | "missing";
  is_late: boolean;
  attempt_number: number;
}

export interface Grade {
  id: number;
  submission: number;
  points: number | null;
  feedback: string;
  status: "draft" | "released";
  graded_by: number;
  graded_at: string;
  released_by: number | null;
  released_at: string | null;
}