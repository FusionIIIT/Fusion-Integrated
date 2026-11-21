import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

/** One lazy chunk per page so Vite splits code properly. */
const InboxPage = lazy(() => import("./pages/InboxPage"));
const OutboxPage = lazy(() => import("./pages/OutboxPage"));
const DraftsPage = lazy(() => import("./pages/DraftsPage"));
const CreateFilePage = lazy(() => import("./pages/CreateFilePage"));
const GovernancePage = lazy(() => import("./pages/GovernancePage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="inbox" replace /> },
  { path: "inbox", element: <InboxPage /> },
  { path: "outbox", element: <OutboxPage /> },
  { path: "drafts", element: <DraftsPage /> },
  { path: "create", element: <CreateFilePage /> },
  {
    path: "governance",
    element: (
      <RequirePermission permission="fts.governance.view">
        <GovernancePage />
      </RequirePermission>
    ),
  },
];
