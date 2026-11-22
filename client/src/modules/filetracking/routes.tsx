import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

const InboxPage = lazy(() => import("./pages/InboxPage"));
const OutboxPage = lazy(() => import("./pages/OutboxPage"));
const CreateFilePage = lazy(() => import("./pages/CreateFilePage"));
const ArchivePage = lazy(() => import("./pages/ArchivePage"));
const GovernancePage = lazy(() => import("./pages/GovernancePage"));

function office(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="inbox" replace /> },
  { path: "inbox", element: office("filetracking.file.view", <InboxPage />) },
  { path: "outbox", element: office("filetracking.file.view", <OutboxPage />) },
  { path: "create", element: office("filetracking.file.create", <CreateFilePage />) },
  { path: "archive", element: office("filetracking.file.view", <ArchivePage />) },
  { path: "governance", element: office("filetracking.governance.view", <GovernancePage />) },
];
