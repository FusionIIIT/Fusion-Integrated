import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { ListPage } from "./pages/ListPage";

const NewPage = lazy(() => import("./pages/NewPage"));
const DetailPage = lazy(() => import("./pages/DetailPage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));
const NotificationsPage = lazy(() => import("./pages/NotificationsPage"));

/** Relative paths under /patents. Each needs a matching nav item in registry.py. */
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "new", element: <NewPage /> },
  { path: "mine", element: <ListPage title="My applications" subtitle="Applications you have submitted" /> },
  { path: "queue", element: <ListPage title="My assignments" subtitle="Applications routed to you" /> },
  { path: "applications", element: <ListPage title="All applications" subtitle="Every application in PMS" /> },
  { path: "applications/:id", element: <DetailPage /> },
  { path: "reports", element: <ReportsPage /> },
  { path: "notifications", element: <NotificationsPage /> },
];
