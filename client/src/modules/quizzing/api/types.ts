export type QuestionType = "MCQ_SINGLE" | "MCQ_MULTI" | "TRUE_FALSE" | "SHORT_ANSWER";

export interface Question {
  id: string;
  question_text: string;
  question_type: QuestionType;
  options: { id: string; text: string }[];
  default_marks: number;
}

export interface Quiz {
  id: string;
  title: string;
  course_code: string;
  start_time: string;
  end_time: string;
  duration_minutes: number;
  status: "DRAFT" | "PUBLISHED" | "CLOSED";
  total_marks: number;
  answer_key_released: boolean;
  grades_released: boolean;
  questions?: { id: string; marks: number; question: Question }[];
}

export interface StudentAnswer {
  id: string;
  question: string;
  question_text?: string;
  submitted_answer: Record<string, any>;
  autograded_score: number | null;
  override_score: number | null;
  final_score: number;
}

export interface QuizAttempt {
  id: string;
  quiz: string;
  quiz_title?: string;
  quiz_duration?: number;
  student_user_id: string;
  started_at: string;
  submitted_at: string | null;
  status: string;
  total_score: number;
  answers: StudentAnswer[];
}
