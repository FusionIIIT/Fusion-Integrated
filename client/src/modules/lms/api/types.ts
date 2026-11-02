export interface CourseWorkspace {
  id: number;
  course_code: string;
  title: string;
  syllabus: string;
  schedule: string;
  instructor_user_id: number;
  is_active: boolean;
  user_role?: "student" | "faculty" | "ta" | "observer";
  can_post_announcements?: boolean;
}

export interface CourseMembership {
  id: number;
  course: number;
  course_code: string;
  course_title: string;
  user_id: number;
  role: "student" | "faculty" | "ta" | "observer";
  can_post_announcements: boolean;
  created_at: string;
}

export interface CourseMaterial {
  id: number;
  course: number;
  title: string;
  description: string;
  section_or_week: string;
  material_type: "file" | "link" | "note";
  file_url: string;
  content: string;
  status: "draft" | "scheduled" | "published";
  scheduled_release_at: string | null;
  published_at: string | null;
  uploaded_by_user_id: number;
}

export interface CourseAnnouncement {
  id: number;
  course: number;
  title: string;
  content: string;
  posted_by_user_id: number;
  is_ta_announcement: boolean;
  posted_at: string;
}

export interface Grade {
  id: number;
  submission: number;
  points: string | null;
  feedback: string;
  status: "draft" | "released";
  graded_by_user_id: number;
  graded_at: string;
  released_at: string | null;
  released_by_user_id: number | null;
}

export interface Assignment {
  id: number;
  course: number;
  title: string;
  instructions: string;
  points_possible: string;
  submission_type: "file" | "text" | "link";
  due_date: string;
  status: "draft" | "scheduled" | "available";
  scheduled_release_at: string | null;
  published_at: string | null;
  created_by_user_id: number;
}

export interface StudentSubmission {
  id: number;
  assignment: number;
  assignment_title: string;
  due_date: string;
  student_user_id: number;
  submission_type: "file" | "text" | "link";
  submission_content: string;
  submitted_at: string;
  status: "submitted" | "late" | "missing";
  grade: Grade | null;
}

export interface GradeChangeLog {
  id: number;
  grade: number;
  old_points: string | null;
  new_points: string;
  reason: string;
  changed_by_user_id: number;
  changed_at: string;
}
