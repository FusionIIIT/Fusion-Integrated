import { lazy } from "react";
import type { RouteObject } from "react-router-dom";

const QuizListPage = lazy(() => import("./pages/QuizListPage"));
const QuizDetailPage = lazy(() => import("./pages/QuizDetailPage"));
const QuizTakePage = lazy(() => import("./pages/QuizTakePage"));
const QuestionBankPage = lazy(() => import("./pages/QuestionBankPage"));
const QuizGradingPage = lazy(() => import("./pages/QuizGradingPage"));

export const routes: RouteObject[] = [
  { index: true, element: <QuizListPage /> },
  { path: "my", element: <QuizListPage /> },
  { path: "question-bank", element: <QuestionBankPage /> },
  { path: ":id", element: <QuizDetailPage /> },
  { path: ":id/take", element: <QuizTakePage /> },
  { path: ":id/submissions", element: <QuizGradingPage /> },
];

