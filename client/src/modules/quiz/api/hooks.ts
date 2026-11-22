import {
  useMutation, useQuery, useQueryClient,
} from "@tanstack/react-query";

import { http } from "../../../lib/http";
import type {
  AttemptDetail, Page, Question, Quiz, QuizAttempt, QuizReport,
} from "./types";

const KEY = "quiz";

export const keys = {
  quizzes: () => [KEY, "quizzes"] as const,
  quiz: (id?: number) => [KEY, "quiz", id] as const,
  questions: (quizId?: number) => [KEY, "questions", quizId] as const,
  bank: (filters?: Record<string, string>) => [KEY, "bank", filters] as const,
  submissions: (quizId?: number) => [KEY, "submissions", quizId] as const,
  evalAttempt: (id?: number) => [KEY, "eval-attempt", id] as const,
  report: (quizId?: number) => [KEY, "report", quizId] as const,
  eligibleQuizzes: () => [KEY, "eligible"] as const,
  eligibleQuiz: (id?: number) => [KEY, "eligible", id] as const,
  attempt: (id?: number) => [KEY, "attempt", id] as const,
  myResults: () => [KEY, "my-results"] as const,
  myResult: (id?: number) => [KEY, "my-result", id] as const,
};

function invalidateAll(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: [KEY] });
}

// -- Professor: Quiz CRUD ---------------------------------------------------

export function useQuizzes() {
  return useQuery({
    queryKey: keys.quizzes(),
    queryFn: async () => (await http.get<Page<Quiz>>("/quiz/quizzes/")).data,
    staleTime: 30_000,
  });
}

export function useQuiz(id?: number) {
  return useQuery({
    queryKey: keys.quiz(id),
    queryFn: async () => (await http.get<Quiz>(`/quiz/quizzes/${id}/`)).data,
    enabled: Boolean(id),
  });
}

export function useCreateQuiz() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<Quiz>) =>
      (await http.post<Quiz>("/quiz/quizzes/", payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useUpdateQuiz() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...payload }: Partial<Quiz> & { id: number }) =>
      (await http.patch<Quiz>(`/quiz/quizzes/${id}/`, payload)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useDeleteQuiz() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await http.delete(`/quiz/quizzes/${id}/`);
    },
    onSuccess: () => invalidateAll(qc),
  });
}

export function usePublishQuiz() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<Quiz>(`/quiz/quizzes/${id}/publish/`)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useCloseQuiz() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<Quiz>(`/quiz/quizzes/${id}/close/`)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useArchiveQuiz() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) =>
      (await http.post<Quiz>(`/quiz/quizzes/${id}/archive/`)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Professor: Questions ---------------------------------------------------

export function useQuizQuestions(quizId?: number) {
  return useQuery({
    queryKey: keys.questions(quizId),
    queryFn: async () =>
      (await http.get<Page<Question>>(`/quiz/quizzes/${quizId}/questions/`)).data,
    enabled: Boolean(quizId),
  });
}

export function useAddQuestion(quizId?: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: Partial<Question>) =>
      (await http.post<Question>(`/quiz/quizzes/${quizId}/questions/`, payload)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.questions(quizId) });
      qc.invalidateQueries({ queryKey: keys.quizzes() });
    },
  });
}

export function useUpdateQuestion(quizId?: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...payload }: Partial<Question> & { id: number }) =>
      (await http.patch<Question>(`/quiz/questions/${id}/`, payload)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.questions(quizId) });
    },
  });
}

export function useDeleteQuestion(quizId?: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      await http.delete(`/quiz/questions/${id}/`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.questions(quizId) });
      qc.invalidateQueries({ queryKey: keys.quizzes() });
    },
  });
}

export function useQuestionBank(filters?: Record<string, string>) {
  return useQuery({
    queryKey: keys.bank(filters),
    queryFn: async () =>
      (await http.get<Page<Question>>("/quiz/bank/", { params: filters })).data,
  });
}

export function useAddBankQuestionToQuiz(quizId?: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (bankQuestionId: number) =>
      (await http.post<Question>(`/quiz/bank/${bankQuestionId}/add-to-quiz/`, {
        quiz_id: quizId,
      })).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.questions(quizId) });
      qc.invalidateQueries({ queryKey: keys.quizzes() });
    },
  });
}

// -- Professor: Evaluation / Submissions ------------------------------------

export function useQuizSubmissions(quizId?: number) {
  return useQuery({
    queryKey: keys.submissions(quizId),
    queryFn: async () =>
      (await http.get<Page<QuizAttempt>>(`/quiz/quizzes/${quizId}/submissions/`)).data,
    enabled: Boolean(quizId),
  });
}

export function useAttemptForEvaluation(attemptId?: number) {
  return useQuery({
    queryKey: keys.evalAttempt(attemptId),
    queryFn: async () =>
      (await http.get<AttemptDetail>(`/quiz/attempts/${attemptId}/evaluate/`)).data,
    enabled: Boolean(attemptId),
  });
}

export function useEvaluateAttempt(quizId?: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      attemptId, responses,
    }: {
      attemptId: number;
      responses: Array<{
        response_id: number;
        marks_obtained: number | null;
        professor_feedback?: string;
        ai_suggested_marks?: number | null;
      }>;
    }) =>
      (await http.post<AttemptDetail>(`/quiz/attempts/${attemptId}/evaluate/`, {
        responses,
      })).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.submissions(quizId) });
      qc.invalidateQueries({ queryKey: keys.report(quizId) });
    },
  });
}

export function useReleaseAttemptResult(quizId?: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (attemptId: number) =>
      (await http.post<QuizAttempt>(`/quiz/attempts/${attemptId}/release/`)).data,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: keys.submissions(quizId) });
      qc.invalidateQueries({ queryKey: keys.report(quizId) });
    },
  });
}

export function useReleaseAllResults() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (quizId: number) =>
      (await http.post<{ released: number }>(`/quiz/quizzes/${quizId}/release-all/`)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useQuizReport(quizId?: number) {
  return useQuery({
    queryKey: keys.report(quizId),
    queryFn: async () =>
      (await http.get<QuizReport>(`/quiz/quizzes/${quizId}/report/`)).data,
    enabled: Boolean(quizId),
  });
}

// -- Student: Quizzes & Taking Attempts -------------------------------------

export function useEligibleQuizzes() {
  return useQuery({
    queryKey: keys.eligibleQuizzes(),
    queryFn: async () => (await http.get<Page<Quiz>>("/quiz/eligible/")).data,
    staleTime: 15_000,
  });
}

export function useEligibleQuiz(id?: number) {
  return useQuery({
    queryKey: keys.eligibleQuiz(id),
    queryFn: async () => (await http.get<Quiz>(`/quiz/eligible/${id}/`)).data,
    enabled: Boolean(id),
  });
}

export function useStartAttempt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (quizId: number) =>
      (await http.post<AttemptDetail>(`/quiz/eligible/${quizId}/start/`)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

export function useAttemptDetail(attemptId?: number, refetchActive = false) {
  return useQuery({
    queryKey: keys.attempt(attemptId),
    queryFn: async () =>
      (await http.get<AttemptDetail>(`/quiz/attempts/${attemptId}/`)).data,
    enabled: Boolean(attemptId),
    refetchInterval: refetchActive ? 15_000 : false,
  });
}

export function useSaveResponse() {
  return useMutation({
    mutationFn: async ({
      attemptId, questionId, response,
    }: {
      attemptId: number;
      questionId: number;
      response: unknown;
    }) =>
      (await http.post<{ saved: boolean }>(`/quiz/attempts/${attemptId}/respond/`, {
        question_id: questionId,
        response,
      })).data,
  });
}

export function useSubmitAttempt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (attemptId: number) =>
      (await http.post<QuizAttempt>(`/quiz/attempts/${attemptId}/submit/`)).data,
    onSuccess: () => invalidateAll(qc),
  });
}

// -- Student: Results -------------------------------------------------------

export function useMyResults() {
  return useQuery({
    queryKey: keys.myResults(),
    queryFn: async () => (await http.get<Page<QuizAttempt>>("/quiz/my-results/")).data,
    staleTime: 30_000,
  });
}

export function useMyResultDetail(attemptId?: number) {
  return useQuery({
    queryKey: keys.myResult(attemptId),
    queryFn: async () =>
      (await http.get<AttemptDetail>(`/quiz/my-results/${attemptId}/`)).data,
    enabled: Boolean(attemptId),
  });
}
