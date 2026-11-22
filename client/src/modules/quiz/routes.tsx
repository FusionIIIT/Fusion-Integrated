import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

const MyQuizzesPage = lazy(() => import("./pages/MyQuizzesPage"));
const MyResultsPage = lazy(() => import("./pages/MyResultsPage"));
const ManageQuizzesPage = lazy(() => import("./pages/ManageQuizzesPage"));
const EvaluatePage = lazy(() => import("./pages/EvaluatePage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));

function office(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="my-quizzes" replace /> },
  { path: "my-quizzes", element: <MyQuizzesPage /> },
  { path: "results", element: <MyResultsPage /> },
  { path: "manage", element: office("quiz.quiz.manage", <ManageQuizzesPage />) },
  { path: "evaluate", element: office("quiz.evaluation.manage", <EvaluatePage />) },
  { path: "reports", element: office("quiz.report.view", <ReportsPage />) },
];
