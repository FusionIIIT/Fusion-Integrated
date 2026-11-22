import React from "react";
import type { RouteObject } from "react-router-dom";
import { QuizListPage } from "./pages/QuizListPage";
import { QuizCreatePage } from "./pages/QuizCreatePage";
import { QuizAttemptPage } from "./pages/QuizAttemptPage";
import { QuizGradingPage } from "./pages/QuizGradingPage";

export const routes: RouteObject[] = [
  { path: "", element: <QuizListPage /> },
  { path: "create", element: <QuizCreatePage /> },
  { path: "attempt/:attemptId", element: <QuizAttemptPage /> },
  { path: "grading/:quizId", element: <QuizGradingPage /> },
];
