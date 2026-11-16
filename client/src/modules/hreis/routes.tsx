import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const Page = lazy(() => import("./HrPage"));
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="records" replace /> },
  { path: "records", element: <Page page="records" /> },
  { path: "leave", element: <Page page="leave" /> },
  { path: "appraisals", element: <Page page="appraisals" /> },
  { path: "claims", element: <Page page="claims" /> },
  { path: "approvals", element: <Page page="approvals" /> },
  { path: "admin", element: <Page page="admin" /> },
  { path: "audit", element: <Page page="audit" /> },
  { path: "notifications", element: <Page page="notifications" /> },
];
