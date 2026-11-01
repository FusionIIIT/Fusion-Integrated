import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const InboxPage = lazy(() => import("./pages/InboxPage"));
const OutboxPage = lazy(() => import("./pages/OutboxPage"));
const CreateFilePage = lazy(() => import("./pages/CreateFilePage"));
const ArchivePage = lazy(() => import("./pages/ArchivePage"));
const GovernancePage = lazy(() => import("./pages/GovernancePage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="inbox" replace /> },
  { path: "inbox", element: <InboxPage /> },
  { path: "outbox", element: <OutboxPage /> },
  { path: "create", element: <CreateFilePage /> },
  { path: "archive", element: <ArchivePage /> },
  { path: "governance", element: <GovernancePage /> },
];

