import { type ReactNode } from "react";
import type { RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";
import ArchivesPage from "./pages/ArchivesPage";
import OperationsPage from "./pages/OperationsPage";
import OverviewPage from "./pages/OverviewPage";

function office(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: office("badms.backup.view", <OverviewPage />) },
  {
    path: "archives",
    element: office("badms.archive.view_self", <ArchivesPage />),
  },
  {
    path: "operations",
    element: office("badms.restore.view_self", <OperationsPage />),
  },
];
