import { lazy } from "react";
import type { RouteObject } from "react-router-dom";

/** One lazy chunk per page. Vite can only split these if the import() argument
 *  is a static literal — a computed path silently bundles everything. */
const LmsDashboardPage = lazy(() => import("./pages/LmsDashboardPage"));
const CourseWorkspacePage = lazy(() => import("./pages/CourseWorkspacePage"));
const MaterialsPage = lazy(() => import("./pages/MaterialsPage"));
const AnnouncementsPage = lazy(() => import("./pages/AnnouncementsPage"));
const AssignmentsPage = lazy(() => import("./pages/AssignmentsPage"));
const StudentAssignmentDetailPage = lazy(() => import("./pages/StudentAssignmentDetailPage"));
const FacultyGradingDashboardPage = lazy(() => import("./pages/FacultyGradingDashboardPage"));
const TaGradingDashboardPage = lazy(() => import("./pages/TaGradingDashboardPage"));
const ReleasedGradesPage = lazy(() => import("./pages/ReleasedGradesPage"));
const ObserverCourseViewPage = lazy(() => import("./pages/ObserverCourseViewPage"));
const ScheduledContentPage = lazy(() => import("./pages/ScheduledContentPage"));

/** Paths are RELATIVE — the shell mounts them under the manifest's basePath (/courses). */
export const routes: RouteObject[] = [
  { index: true, element: <LmsDashboardPage /> },
  { path: "scheduled", element: <ScheduledContentPage /> },
  { path: ":courseId", element: <CourseWorkspacePage /> },
  { path: ":courseId/materials", element: <MaterialsPage /> },
  { path: ":courseId/announcements", element: <AnnouncementsPage /> },
  { path: ":courseId/assignments", element: <AssignmentsPage /> },
  { path: ":courseId/assignments/:assignmentId", element: <StudentAssignmentDetailPage /> },
  { path: ":courseId/grading", element: <FacultyGradingDashboardPage /> },
  { path: ":courseId/ta-grading", element: <TaGradingDashboardPage /> },
  { path: ":courseId/grades", element: <ReleasedGradesPage /> },
  { path: ":courseId/observer", element: <ObserverCourseViewPage /> },
];

export default routes;
