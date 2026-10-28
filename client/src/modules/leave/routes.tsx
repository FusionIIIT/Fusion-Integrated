import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

/** One lazy chunk for the module's pages. Every entry here has a matching nav
 *  item in the server's registry.py, so the sidebar never links nowhere. */
const page = (name: keyof typeof import("./pages/LeavePages")) =>
  lazy(() =>
    import("./pages/LeavePages").then((m) => ({ default: m[name] })));

const MyLeavePage = page("MyLeavePage");
const BalancesPage = page("BalancesPage");
const SubstitutePage = page("SubstitutePage");
const QueuePage = page("QueuePage");
const CalendarPage = page("CalendarPage");
const PolicyPage = page("PolicyPage");
const ReportsPage = page("ReportsPage");

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="my-leave" replace /> },
  { path: "my-leave", element: <MyLeavePage /> },
  { path: "balances", element: <BalancesPage /> },
  { path: "substitute", element: <SubstitutePage /> },
  { path: "queue", element: <QueuePage /> },
  { path: "calendar", element: <CalendarPage /> },
  { path: "policy", element: <PolicyPage /> },
  { path: "reports", element: <ReportsPage /> },
];
