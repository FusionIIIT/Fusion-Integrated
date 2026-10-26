import { Navigate, type RouteObject } from "react-router-dom";
import LeaveRequestList from "./pages/LeaveRequestList";
import LeaveBalanceDashboard from "./pages/LeaveBalanceDashboard";
import LeaveTypeCatalog from "./pages/LeaveTypeCatalog";
import LeavePolicyEditor from "./pages/LeavePolicyEditor";

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="requests" replace /> },
  { path: "requests", element: <LeaveRequestList /> },
  { path: "balances", element: <LeaveBalanceDashboard /> },
  { path: "types", element: <LeaveTypeCatalog /> },
  { path: "policies", element: <LeavePolicyEditor /> },
];
