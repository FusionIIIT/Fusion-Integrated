import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

const InboxPage = lazy(() => import("./pages/InboxPage"));
const OutboxPage = lazy(() => import("./pages/OutboxPage"));
const DraftsPage = lazy(() => import("./pages/DraftsPage"));
const CreateFilePage = lazy(() => import("./pages/CreateFilePage"));

function guarded(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="inbox" replace /> },
  { path: "inbox", element: guarded("fts.file.view", <InboxPage />) },
  { path: "outbox", element: guarded("fts.file.view", <OutboxPage />) },
  { path: "drafts", element: guarded("fts.file.view", <DraftsPage />) },
  { path: "create", element: guarded("fts.file.create", <CreateFilePage />) },
];
