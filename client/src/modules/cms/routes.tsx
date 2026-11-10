import { lazy } from "react";
import { type RouteObject } from "react-router-dom";

const CmsWorkspace = lazy(() => import("./pages/CmsWorkspace"));

export const routes: RouteObject[] = [
  { index: true, element: <CmsWorkspace defaultTab="my_complaints" /> },
  { path: "complaints", element: <CmsWorkspace defaultTab="my_complaints" /> },
  { path: "queue", element: <CmsWorkspace defaultTab="handler" /> },
  { path: "escalations", element: <CmsWorkspace defaultTab="escalations" /> },
  { path: "announcements", element: <CmsWorkspace defaultTab="announcements" /> },
  { path: "reports", element: <CmsWorkspace defaultTab="reports" /> },
  { path: "roles", element: <CmsWorkspace defaultTab="roles" /> },
];
