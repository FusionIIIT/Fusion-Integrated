import { Navigate, type RouteObject } from "react-router-dom";

import BookingsPage from "./pages/BookingsPage";
import InventoryPage from "./pages/InventoryPage";
import OfflineBookingPage from "./pages/OfflineBookingPage";
import OperationsPage from "./pages/OperationsPage";
import ReportsPage from "./pages/ReportsPage";

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="bookings" replace /> },
  { path: "bookings", element: <BookingsPage /> },
  { path: "operations", element: <OperationsPage /> },
  { path: "offline-booking", element: <OfflineBookingPage /> },
  { path: "inventory", element: <InventoryPage /> },
  { path: "reports", element: <ReportsPage /> },
];
