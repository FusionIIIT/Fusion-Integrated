export type QuizStatus = "draft" | "scheduled" | "available" | "closed" | "archived";
export type AttemptStatus = "in_progress" | "submitted" | "partially_evaluated" | "evaluated" | "released";
export type QuestionType = "mcq" | "msq" | "tf" | "fitb" | "short";

export interface OptionItem {
  id: string;
  text: string;
}

export interface Question {
  id: number;
  quiz: number;
  question_type: QuestionType;
  text: string;
  image_url?: string;
  marks: number;
  negative_marks: number;
  topic: string;
  difficulty: "easy" | "medium" | "hard" | "";
  order: number;
  is_bank_question: boolean;
  options?: OptionItem[] | null;
  correct_answer?: unknown;
  reference_answer?: string;
  evaluation_criteria?: string;
}

export interface Quiz {
  id: number;
  title: string;
  description: string;
  course: string;
  instructions: string;
  status: QuizStatus;
  duration_minutes: number;
  max_marks: number;
  passing_marks: number | null;
  max_attempts: number;
  start_at: string | null;
  close_at: string | null;
  allow_back_navigation: boolean;
  one_question_at_a_time: boolean;
  randomize_questions: boolean;
  randomize_options: boolean;
  allow_unanswered: boolean;
  tab_block: boolean;
  negative_marking: boolean;
  result_visibility: "immediate" | "after_release" | "never";
  question_count: number;
  attempt_count: number;
  created_by_user_id: number;
  created_at: string;
  updated_at: string;
}

export interface AttemptResponse {
  id: number;
  question: number;
  question_text: string;
  question_type: string;
  marks: number;
  options?: OptionItem[] | null;
  correct_answer?: unknown;
  response: unknown;
  is_correct: boolean | null;
  marks_obtained: number | null;
  ai_suggested_marks: number | null;
  ai_reasoning: string;
  professor_feedback: string;
  evaluated_at: string | null;
}

export interface QuizAttempt {
  id: number;
  quiz: number;
  quiz_title: string;
  quiz_course: string;
  user_id: number;
  status: AttemptStatus;
  started_at: string;
  submitted_at: string | null;
  attempt_number: number;
  score: number | null;
  percentage: number | null;
  passed: boolean | null;
  time_taken_seconds: number | null;
  tab_violations: number;
  created_at: string;
}

export interface AttemptDetail extends QuizAttempt {
  time_remaining_seconds: number | null;
  duration_minutes: number;
  allow_back_navigation: boolean;
  one_question_at_a_time: boolean;
  randomize_questions: boolean;
  allow_unanswered: boolean;
  tab_block: boolean;
  instructions: string;
  questions: Question[];
  responses: AttemptResponse[];
}

export interface QuizReport {
  quiz_id: number;
  quiz_title: string;
  total_submissions: number;
  average_score: number | null;
  highest_score: number | null;
  lowest_score: number | null;
  pass_percentage: number | null;
  submissions: QuizAttempt[];
}

export interface Page<T> {
  results: T[];
}
