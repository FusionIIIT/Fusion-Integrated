import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

const NewBookingPage = lazy(() => import("./pages/NewBookingPage"));
const MyBookingsPage = lazy(() => import("./pages/MyBookingsPage"));
const TariffCardPage = lazy(() => import("./pages/TariffCardPage"));
const BookingRequisitionsPage = lazy(() => import("./pages/BookingRequisitionsPage"));
const StayManagementPage = lazy(() => import("./pages/StayManagementPage"));
const MessManagementPage = lazy(() => import("./pages/MessManagementPage"));
const BillingSettlementPage = lazy(() => import("./pages/BillingSettlementPage"));
const InventoryPage = lazy(() => import("./pages/InventoryPage"));
const CaretakerReportsPage = lazy(() => import("./pages/CaretakerReportsPage"));
const ExecutiveApprovalsPage = lazy(() => import("./pages/ExecutiveApprovalsPage"));
const SupervisorReportsPage = lazy(() => import("./pages/SupervisorReportsPage"));
const OperationalRolePage = lazy(() => import("./pages/OperationalRolePage"));

function office(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="my-bookings" replace /> },
  { path: "booking/new", element: <NewBookingPage /> },
  { path: "my-bookings", element: <MyBookingsPage /> },
  { path: "tariffs", element: <TariffCardPage /> },
  { path: "bookings", element: office("vh.booking.review", <BookingRequisitionsPage />) },
  { path: "stays", element: office("vh.stay.manage", <StayManagementPage />) },
  { path: "meals", element: office("vh.meal.manage", <MessManagementPage />) },
  { path: "billing", element: office("vh.bill.manage", <BillingSettlementPage />) },
  { path: "inventory", element: office("vh.inventory.manage", <InventoryPage />) },
  { path: "caretaker-reports", element: office("vh.report.view", <CaretakerReportsPage />) },
  { path: "approvals", element: office("vh.booking.approve", <ExecutiveApprovalsPage />) },
  { path: "supervisor-reports", element: office("vh.report.manage", <SupervisorReportsPage />) },
  { path: "roles", element: office("vh.role.assign", <OperationalRolePage />) },
];
