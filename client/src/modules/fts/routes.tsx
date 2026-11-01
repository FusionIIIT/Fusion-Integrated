import { lazy, Suspense } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const InboxPage = lazy(() => import("./pages/InboxPage"));
const OutboxPage = lazy(() => import("./pages/OutboxPage"));
const DraftsPage = lazy(() => import("./pages/DraftsPage"));
const DraftFilePage = lazy(() => import("./pages/DraftFilePage"));
const FileDetailPage = lazy(() => import("./pages/FileDetailPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="inbox" replace /> },
  { path: "inbox", element: <Suspense fallback={null}><InboxPage /></Suspense> },
  { path: "outbox", element: <Suspense fallback={null}><OutboxPage /></Suspense> },
  { path: "drafts", element: <Suspense fallback={null}><DraftsPage /></Suspense> },
  { path: "files/new", element: <Suspense fallback={null}><DraftFilePage /></Suspense> },
  { path: "files/:id", element: <Suspense fallback={null}><FileDetailPage /></Suspense> },
  { path: "files/:id/edit", element: <Suspense fallback={null}><DraftFilePage /></Suspense> },
];
