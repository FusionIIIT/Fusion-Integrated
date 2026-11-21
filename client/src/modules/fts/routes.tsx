import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

/** One lazy chunk per page so Vite splits code properly. */
const InboxPage = lazy(() => import("./pages/InboxPage"));
const OutboxPage = lazy(() => import("./pages/OutboxPage"));
const DraftsPage = lazy(() => import("./pages/DraftsPage"));
const CreateFilePage = lazy(() => import("./pages/CreateFilePage"));
const GovernancePage = lazy(() => import("./pages/GovernancePage"));

function guarded(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="inbox" replace /> },
  { path: "inbox", element: guarded("fts.file.view", <InboxPage />) },
  { path: "outbox", element: guarded("fts.file.view", <OutboxPage />) },
  { path: "drafts", element: guarded("fts.file.create", <DraftsPage />) },
  { path: "create", element: guarded("fts.file.create", <CreateFilePage />) },
  { path: "governance", element: guarded("fts.governance.view", <GovernancePage />) },
];
