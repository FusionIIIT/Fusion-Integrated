import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const WorkRequestsPage = lazy(() => import("./pages/WorkRequestsPage"));
const NewRequestPage = lazy(() => import("./pages/NewRequestPage"));
const ApprovalsPage = lazy(() => import("./pages/ApprovalsPage"));
const ContractorsPage = lazy(() => import("./pages/ContractorsPage"));
const InventoryPage = lazy(() => import("./pages/InventoryPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="requests" replace /> },
  { path: "requests", element: <WorkRequestsPage /> },
  { path: "new-request", element: <NewRequestPage /> },
  { path: "approvals", element: <ApprovalsPage /> },
  { path: "contractors", element: <ContractorsPage /> },
  { path: "inventory", element: <InventoryPage /> },
];

