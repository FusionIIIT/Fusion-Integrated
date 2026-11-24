import { Navigate, type RouteObject } from "react-router-dom";
import ApplyLeavePage from "./pages/ApplyLeavePage";
import MyLeavesPage from "./pages/MyLeavesPage";
import LeaveBalancePage from "./pages/LeaveBalancePage";
import LeaveApprovalsPage from "./pages/LeaveApprovalsPage";

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="apply" replace /> },
  { path: "apply", element: <ApplyLeavePage /> },
  { path: "mine", element: <MyLeavesPage /> },
  { path: "balance", element: <LeaveBalancePage /> },
  { path: "approvals", element: <LeaveApprovalsPage /> },
];
