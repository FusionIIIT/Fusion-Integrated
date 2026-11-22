import type { Quiz, QuizAttempt } from "./types";

const BASE = "/api/v1/quiz";

export async function fetchQuizzes(courseId?: number): Promise<Quiz[]> {
  const url = courseId ? `${BASE}/quizzes/?course_id=${courseId}` : `${BASE}/quizzes/`;
  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to fetch quizzes");
  return res.json();
}

export async function fetchQuiz(id: number): Promise<Quiz> {
  const res = await fetch(`${BASE}/quizzes/${id}/`);
  if (!res.ok) throw new Error("Failed to fetch quiz");
  return res.json();
}

export async function createQuiz(data: Partial<Quiz>): Promise<Quiz> {
  const res = await fetch(`${BASE}/quizzes/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to create quiz");
  return res.json();
}

export async function publishQuiz(id: number): Promise<Quiz> {
  const res = await fetch(`${BASE}/quizzes/${id}/publish/`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to publish quiz");
  return res.json();
}

export async function startAttempt(quizId: number): Promise<QuizAttempt> {
  const res = await fetch(`${BASE}/quizzes/${quizId}/start/`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to start attempt");
  return res.json();
}

export async function saveAttemptAnswer(attemptId: number, questionId: number, answer: any): Promise<any> {
  const res = await fetch(`${BASE}/attempts/${attemptId}/save/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question_id: questionId, answer }),
  });
  if (!res.ok) throw new Error("Failed to save answer");
  return res.json();
}

export async function recordViolation(attemptId: number): Promise<any> {
  const res = await fetch(`${BASE}/attempts/${attemptId}/violation/`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to record violation");
  return res.json();
}

export async function submitAttempt(attemptId: number): Promise<QuizAttempt> {
  const res = await fetch(`${BASE}/attempts/${attemptId}/submit/`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to submit attempt");
  return res.json();
}
