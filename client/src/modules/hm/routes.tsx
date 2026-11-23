import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";
import { RequirePermission } from "../../auth/RequirePermission";

const AccommodationPage = lazy(() => import("./pages/AccommodationPage"));
const RoomsPage = lazy(() => import("./pages/RoomsPage"));
const AttendancePage = lazy(() => import("./pages/AttendancePage"));
const LeavePage = lazy(() => import("./pages/LeavePage"));
const ComplaintsPage = lazy(() => import("./pages/ComplaintsPage"));
const GuestBookingsPage = lazy(() => import("./pages/GuestBookingsPage"));
const ExtendedStaysPage = lazy(() => import("./pages/ExtendedStaysPage"));
const FinesPage = lazy(() => import("./pages/FinesPage"));
const InventoryPage = lazy(() => import("./pages/InventoryPage"));
const GuardShiftsPage = lazy(() => import("./pages/GuardShiftsPage"));
const NoticesPage = lazy(() => import("./pages/NoticesPage"));
const HostelsPage = lazy(() => import("./pages/HostelsPage"));
const RoleBindingsPage = lazy(() => import("./pages/RoleBindingsPage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));

function guarded(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="accommodation" replace /> },
  { path: "accommodation", element: guarded("hm.accommodation_request.view", <AccommodationPage />) },
  { path: "rooms", element: guarded("hm.room.view", <RoomsPage />) },
  { path: "attendance", element: guarded("hm.attendance.view", <AttendancePage />) },
  { path: "leave", element: guarded("hm.leave_request.view", <LeavePage />) },
  { path: "complaints", element: guarded("hm.complaint.view", <ComplaintsPage />) },
  { path: "guest-bookings", element: guarded("hm.guest_booking.view", <GuestBookingsPage />) },
  { path: "extended-stays", element: guarded("hm.extended_stay_request.view", <ExtendedStaysPage />) },
  { path: "fines", element: guarded("hm.fine.view", <FinesPage />) },
  { path: "inventory", element: guarded("hm.inventory_item.view", <InventoryPage />) },
  { path: "guard-shifts", element: guarded("hm.guard_shift.view", <GuardShiftsPage />) },
  { path: "notices", element: guarded("hm.notice.view", <NoticesPage />) },
  { path: "hostels", element: guarded("hm.hostel.view", <HostelsPage />) },
  { path: "assignments", element: guarded("hm.hostel_role_binding.view", <RoleBindingsPage />) },
  { path: "reports", element: guarded("hm.report.view", <ReportsPage />) },
];
