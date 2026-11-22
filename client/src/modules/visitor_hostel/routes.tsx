import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import { RequirePermission } from "../../auth/RequirePermission";

const BookingPage = lazy(() => import("./pages/BookingPage"));
const MyBookingsPage = lazy(() => import("./pages/MyBookingsPage"));
const QueuePage = lazy(() => import("./pages/QueuePage"));
const StaysPage = lazy(() => import("./pages/StaysPage"));
const BillingPage = lazy(() => import("./pages/BillingPage"));
const InventoryPage = lazy(() => import("./pages/InventoryPage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));

function office(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "book", element: office(
    "visitor_hostel.booking.create", <BookingPage />,
  ) },
  { path: "mine", element: office(
    "visitor_hostel.booking.view_self", <MyBookingsPage />,
  ) },
  { path: "queue", element: office(
    "visitor_hostel.booking.review", <QueuePage />,
  ) },
  { path: "stays", element: office(
    "visitor_hostel.stay.update", <StaysPage />,
  ) },
  { path: "billing", element: office(
    "visitor_hostel.bill.manage", <BillingPage />,
  ) },
  { path: "inventory", element: office(
    "visitor_hostel.inventory.manage", <InventoryPage />,
  ) },
  { path: "approvals", element: office(
    "visitor_hostel.booking.approve", <QueuePage />,
  ) },
  { path: "replenishment", element: office(
    "visitor_hostel.replenishment.approve", <InventoryPage />,
  ) },
  { path: "reports", element: office(
    "visitor_hostel.report.view", <ReportsPage />,
  ) },
];
