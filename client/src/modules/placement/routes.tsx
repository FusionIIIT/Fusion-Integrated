import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

/** One lazy chunk per page. */
const PostingsPage = lazy(() => import("./pages/PostingsPage"));
const MyApplicationsPage = lazy(() => import("./pages/MyApplicationsPage"));
const ApplicationsPage = lazy(() => import("./pages/ApplicationsPage"));
const OffersPage = lazy(() => import("./pages/OffersPage"));
const CompaniesPage = lazy(() => import("./pages/CompaniesPage"));
const InterviewsPage = lazy(() => import("./pages/InterviewsPage"));
const AnnouncementsPage = lazy(() => import("./pages/AnnouncementsPage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));
const StudentCpiPage = lazy(() => import("./pages/StudentCpiPage"));
const RecordsPage = lazy(() => import("./pages/RecordsPage"));
const ProfilePage = lazy(() => import("./pages/ProfilePage"));
const RegistrationPage = lazy(() => import("./pages/RegistrationPage"));
const RegistrationApprovalsPage = lazy(
  () => import("./pages/RegistrationApprovalsPage"));

/** Paths are RELATIVE — the shell mounts them under the manifest's basePath. */
// An office page, for the roles its nav item's required_permission names (registry.py).
function office(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="postings" replace /> },
  { path: "registration", element: <RegistrationPage /> },
  { path: "registration-approvals",
    element: office("placement.registration.manage", <RegistrationApprovalsPage />) },
  { path: "profile", element: <ProfilePage /> },
  { path: "postings", element: <PostingsPage /> },
  { path: "mine", element: <MyApplicationsPage /> },
  { path: "offers", element: <OffersPage /> },
  { path: "applications", element: <ApplicationsPage /> },
  { path: "companies", element: office("placement.company.manage", <CompaniesPage />) },
  { path: "interviews",
    element: office("placement.interview.create", <InterviewsPage />) },
  { path: "announcements", element: <AnnouncementsPage /> },
  { path: "students-cpi",
    element: office("placement.academic_directory.view", <StudentCpiPage />) },
  { path: "records",
    element: office("placement.record.manage", <RecordsPage />) },
  { path: "reports", element: <ReportsPage /> },
];
