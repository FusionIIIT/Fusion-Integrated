import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

/**
 * One lazy chunk per page. Vite can split these cleanly when the import()
 * argument is a static string literal.
 */
const BookAccommodationPage = lazy(() => import("./pages/BookAccommodationPage"));
const MyBookingsPage = lazy(() => import("./pages/MyBookingsPage"));
const BookingRequisitionsPage = lazy(() => import("./pages/BookingRequisitionsPage"));
const HostelApprovalsPage = lazy(() => import("./pages/HostelApprovalsPage"));
const StaysAndBillingPage = lazy(() => import("./pages/StaysAndBillingPage"));
const MessAndMealsPage = lazy(() => import("./pages/MessAndMealsPage"));
const HostelInventoryPage = lazy(() => import("./pages/HostelInventoryPage"));
const VHReportsPage = lazy(() => import("./pages/VHReportsPage"));

/**
 * Paths are RELATIVE — mounted under the module's basePath ("/vh").
 * Every path here has a matching entry in modules/vh/registry.py NAV_ITEMS.
 */
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="bookings" replace /> },
  { path: "request", element: <BookAccommodationPage /> },
  { path: "bookings", element: <MyBookingsPage /> },
  { path: "manage", element: <BookingRequisitionsPage /> },
  { path: "approvals", element: <HostelApprovalsPage /> },
  { path: "stays", element: <StaysAndBillingPage /> },
  { path: "meals", element: <MessAndMealsPage /> },
  { path: "inventory", element: <HostelInventoryPage /> },
  { path: "reports", element: <VHReportsPage /> },
];

