export interface Quiz {
  id: number;
  course_id: number;
  title: string;
  instructions: string;
  status: "DRAFT" | "DRAFT_CONFIGURED" | "READY_TO_PUBLISH" | "SCHEDULED" | "AVAILABLE" | "CLOSED" | "ARCHIVED";
  duration_minutes: number;
  max_attempts: number;
  start_at: string | null;
  close_at: string | null;
  created_at: string;
  settings?: QuizSettings;
  questions?: QuizQuestion[];
}

export interface QuizSettings {
  allow_unanswered: boolean;
  back_navigation: boolean;
  tab_violation_limit: number;
  negative_marking_enabled: boolean;
  result_visibility: "FULL" | "MARKS_ONLY" | "HIDDEN";
}

export interface QuizOption {
  id: number;
  option_id: string;
  option_text: string;
}

export interface QuizQuestion {
  id: number;
  quiz_id: number;
  question_text: string;
  question_type: "MCQ" | "MSQ" | "TF" | "FIB" | "SHORT" | "LONG";
  marks: string;
  negative_marks: string;
  correct: string[];
  position: number;
  options?: QuizOption[];
}

export interface QuizAttempt {
  id: number;
  quiz_id: number;
  student_id: number;
  status: "STARTED" | "SUBMITTED";
  deadline_at: string;
  tab_violations: number;
  submitted_at: string | null;
  responses?: AttemptResponse[];
  result?: QuizResult;
  created_at: string;
}

export interface AttemptResponse {
  id: number;
  attempt_id: number;
  question_id: number;
  answer: any;
  saved_at: string;
}

export interface QuizResult {
  id: number;
  attempt_id: number;
  status: "NOT_EVALUATED" | "PARTIALLY_EVALUATED" | "EVALUATED" | "RELEASED";
  marks_obtained: string;
  percentage: string;
  passed: boolean;
}

