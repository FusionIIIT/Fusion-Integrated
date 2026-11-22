import { lazy, type ReactNode } from "react";
import type { RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

const OapDashboardPage = lazy(() => import("./pages/OapDashboardPage"));
const StudentLeavePage = lazy(() => import("./pages/StudentLeavePage"));
const BonafidePage = lazy(() => import("./pages/BonafidePage"));
const NoDuesPage = lazy(() => import("./pages/NoDuesPage"));
const BranchChangePage = lazy(() => import("./pages/BranchChangePage"));
const ApprovalQueuePage = lazy(() => import("./pages/ApprovalQueuePage"));
const AdminBonafidePage = lazy(() => import("./pages/AdminBonafidePage"));
const AdminNoDuesPage = lazy(() => import("./pages/AdminNoDuesPage"));

function office(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <OapDashboardPage /> },
  { path: "leave", element: <StudentLeavePage /> },
  { path: "bonafide", element: <BonafidePage /> },
  { path: "no-dues", element: <NoDuesPage /> },
  { path: "branch-change", element: <BranchChangePage /> },
  { path: "approvals", element: office("oap.leave.approve", <ApprovalQueuePage />) },
  { path: "admin/bonafide", element: office("oap.bonafide.issue", <AdminBonafidePage />) },
  { path: "admin/no-dues", element: office("oap.nodues.finalize", <AdminNoDuesPage />) },
];
