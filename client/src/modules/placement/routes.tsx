import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

/** One lazy chunk per page. Vite can only split these if the import() argument
 *  is a static literal — a computed path silently bundles everything. */
const PostingsPage = lazy(() => import("./pages/PostingsPage"));
const MyApplicationsPage = lazy(() => import("./pages/MyApplicationsPage"));
const ApplicationsPage = lazy(() => import("./pages/ApplicationsPage"));
const OffersPage = lazy(() => import("./pages/OffersPage"));
const ProfilePage = lazy(() => import("./pages/ProfilePage"));
const CompaniesPage = lazy(() => import("./pages/CompaniesPage"));
const InterviewsPage = lazy(() => import("./pages/InterviewsPage"));
const AnnouncementsPage = lazy(() => import("./pages/AnnouncementsPage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));
const StudentCpiPage = lazy(() => import("./pages/StudentCpiPage"));
const RegistrationPage = lazy(() => import("./pages/RegistrationPage"));
const RegistrationApprovalsPage = lazy(
  () => import("./pages/RegistrationApprovalsPage"));

/** Paths are RELATIVE — the shell mounts them under the manifest's basePath.
 *
 *  Every entry here has a matching nav item in the server's registry.py, and
 *  that correspondence matters: the sidebar is built server-side, so a nav item
 *  without a route here renders a link that goes nowhere. */
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="postings" replace /> },
  { path: "registration", element: <RegistrationPage /> },
  { path: "registration-approvals", element: <RegistrationApprovalsPage /> },
  { path: "postings", element: <PostingsPage /> },
  { path: "mine", element: <MyApplicationsPage /> },
  { path: "offers", element: <OffersPage /> },
  { path: "profile", element: <ProfilePage /> },
  { path: "applications", element: <ApplicationsPage /> },
  { path: "companies", element: <CompaniesPage /> },
  { path: "interviews", element: <InterviewsPage /> },
  { path: "announcements", element: <AnnouncementsPage /> },
  { path: "students-cpi", element: <StudentCpiPage /> },
  { path: "reports", element: <ReportsPage /> },
];
