import type { RouteObject } from "react-router-dom";
import { RequirePermission } from "../../auth/RequirePermission";
import { VmsHomePage, HostInboxPage, VmsVisitsPage, EventAdminPage, EventOperationsPage } from "./views";

export const routes: RouteObject[] = [
  { index: true, element: <VmsHomePage /> },
  { path: "visits", element: <RequirePermission permission="vms.visit_request.view"><VmsVisitsPage /></RequirePermission> },
  { path: "inbox", element: <RequirePermission permission="vms.visit_request.approve"><HostInboxPage /></RequirePermission> },
  { path: "admin-review", element: <RequirePermission permission="vms.visit_request.approve"><HostInboxPage admin /></RequirePermission> },
  { path: "admin/events", element: <RequirePermission permission="vms.event.manage"><EventAdminPage /></RequirePermission> },
  { path: "security/events", element: <RequirePermission permission="vms.event.view"><EventOperationsPage /></RequirePermission> },
];
