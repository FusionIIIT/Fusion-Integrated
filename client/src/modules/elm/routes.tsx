import type { RouteObject } from "react-router-dom";
import { ApplyLeavePage } from "./pages/ApplyLeavePage";
import { MyLeavesPage } from "./pages/MyLeavesPage";
import { LeaveApprovalsPage } from "./pages/LeaveApprovalsPage";
import { SubstituteRequestsPage } from "./pages/SubstituteRequestsPage";
import { LeaveBalancePage } from "./pages/LeaveBalancePage";

export const routes: RouteObject[] = [
  { path: "", element: <MyLeavesPage /> },
  { path: "apply", element: <ApplyLeavePage /> },
  { path: "mine", element: <MyLeavesPage /> },
  { path: "balances", element: <LeaveBalancePage /> },
  { path: "substitute", element: <SubstituteRequestsPage /> },
  { path: "approvals", element: <LeaveApprovalsPage /> },
];
