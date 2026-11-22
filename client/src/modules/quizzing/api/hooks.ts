import { useState, useEffect, useCallback } from "react";
import { http } from "../../../lib/http";
import type { Quiz, QuizAttempt } from "./types";

export function useQuizzes(mode: "student" | "faculty" = "student") {
  const [quizzes, setQuizzes] = useState<Quiz[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchQuizzes = useCallback(async () => {
    try {
      setLoading(true);
      const res = await http.get<Quiz[]>(`/quizzing/quizzes/?mode=${mode}`);
      setQuizzes(res.data);
    } finally {
      setLoading(false);
    }
  }, [mode]);

  useEffect(() => { fetchQuizzes(); }, [fetchQuizzes]);
  return { quizzes, loading, refetch: fetchQuizzes };
}

export function useQuizDetail(quizId: string) {
  const [quiz, setQuiz] = useState<Quiz | null>(null);
  const fetchDetail = useCallback(async () => {
    if (!quizId) return;
    const res = await http.get<Quiz>(`/quizzing/quizzes/${quizId}/`);
    setQuiz(res.data);
  }, [quizId]);
  useEffect(() => { fetchDetail(); }, [fetchDetail]);
  return { quiz, refetch: fetchDetail };
}

export function useQuizAttempt(attemptId: string) {
  const [attempt, setAttempt] = useState<QuizAttempt | null>(null);
  const [loading, setLoading] = useState(true);
  const fetchAttempt = useCallback(async () => {
    if (!attemptId) return;
    try {
      setLoading(true);
      const res = await http.get<QuizAttempt>(`/quizzing/attempts/${attemptId}/`);
      setAttempt(res.data);
    } finally {
      setLoading(false);
    }
  }, [attemptId]);
  useEffect(() => { fetchAttempt(); }, [fetchAttempt]);
  return { attempt, loading, refetch: fetchAttempt };
}

export function useQuizSubmissions(quizId: string) {
  const [submissions, setSubmissions] = useState<QuizAttempt[]>([]);
  const [loading, setLoading] = useState(true);
  const fetchSubmissions = useCallback(async () => {
    if (!quizId) return;
    try {
      setLoading(true);
      const res = await http.get<QuizAttempt[]>(`/quizzing/quizzes/${quizId}/submissions/`);
      setSubmissions(res.data);
    } finally {
      setLoading(false);
    }
  }, [quizId]);
  useEffect(() => { fetchSubmissions(); }, [fetchSubmissions]);
  return { submissions, loading, refetch: fetchSubmissions };
}

export const quizApi = {
  createQuiz: (d: any) => http.post<Quiz>("/quizzing/quizzes/", d).then((r) => r.data),
  publishQuiz: (id: string) => http.post<Quiz>(`/quizzing/quizzes/${id}/publish/`).then((r) => r.data),
  startAttempt: (id: string) => http.post<QuizAttempt>(`/quizzing/quizzes/${id}/start/`).then((r) => r.data),
  saveAnswer: (aid: string, qid: string, ans: any) => http.post(`/quizzing/attempts/${aid}/`, { action: "save", question_id: qid, submitted_answer: ans }),
  submitAttempt: (aid: string, auto: boolean = false) => http.post<QuizAttempt>(`/quizzing/attempts/${aid}/`, { action: "submit", autosubmit: auto }).then((r) => r.data),
  logIntegrity: (aid: string, ev: string, det: string = "") => http.post(`/quizzing/attempts/${aid}/`, { action: "integrity", event_type: ev, details: det }),
  overrideScore: (ansId: string, score: number) => http.post(`/quizzing/answers/${ansId}/override/`, { override_score: score }),
  toggleRelease: (id: string, type: "key" | "grades", val: boolean) => http.post(`/quizzing/quizzes/${id}/release-${type}/`, { release: val }),
};
