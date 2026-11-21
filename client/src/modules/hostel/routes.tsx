import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

/** One lazy chunk per page. Vite can only split these if the import() argument
 *  is a static literal — a computed path silently bundles everything. */
const HostelDashboardPage = lazy(() => import("./pages/HostelDashboardPage"));
const HostelMasterPage = lazy(() => import("./pages/HostelMasterPage"));
const AllotmentManagementPage = lazy(() => import("./pages/AllotmentManagementPage"));
const RoomOccupancyPage = lazy(() => import("./pages/RoomOccupancyPage"));
const AttendancePage = lazy(() => import("./pages/AttendancePage"));
const LeaveManagementPage = lazy(() => import("./pages/LeaveManagementPage"));
const ComplaintManagementPage = lazy(() => import("./pages/ComplaintManagementPage"));
const GuestRoomPage = lazy(() => import("./pages/GuestRoomPage"));
const ExtendedStayPage = lazy(() => import("./pages/ExtendedStayPage"));
const FineManagementPage = lazy(() => import("./pages/FineManagementPage"));
const InventoryStaffPage = lazy(() => import("./pages/InventoryStaffPage"));
const SecurityShiftsPage = lazy(() => import("./pages/SecurityShiftsPage"));
const NoticeBoardPage = lazy(() => import("./pages/NoticeBoardPage"));
const ReportsPage = lazy(() => import("./pages/ReportsPage"));

/** Paths are RELATIVE — the shell mounts them under the manifest's basePath (/hostel).
 *  Every entry here corresponds to a nav item in modules/hostel/registry.py. */
export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="dashboard" replace /> },
  { path: "dashboard", element: <HostelDashboardPage /> },
  { path: "masters", element: <HostelMasterPage /> },
  { path: "allotments", element: <AllotmentManagementPage /> },
  { path: "occupancy", element: <RoomOccupancyPage /> },
  { path: "attendance", element: <AttendancePage /> },
  { path: "leaves", element: <LeaveManagementPage /> },
  { path: "complaints", element: <ComplaintManagementPage /> },
  { path: "guest-rooms", element: <GuestRoomPage /> },
  { path: "extended-stay", element: <ExtendedStayPage /> },
  { path: "fines", element: <FineManagementPage /> },
  { path: "inventory", element: <InventoryStaffPage /> },
  { path: "security", element: <SecurityShiftsPage /> },
  { path: "notices", element: <NoticeBoardPage /> },
  { path: "reports", element: <ReportsPage /> },
];
