import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const MmsPlaceholderPage = lazy(() => import("./pages/MmsPlaceholderPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="menu" replace /> },
  { path: "registration", element: <MmsPlaceholderPage title="Mess Registration" /> },
  { path: "menu", element: <MmsPlaceholderPage title="Mess Menu" /> },
  { path: "rebates", element: <MmsPlaceholderPage title="Mess Rebates" /> },
  { path: "special-food", element: <MmsPlaceholderPage title="Special Food Requests" /> },
  { path: "bills", element: <MmsPlaceholderPage title="Mess Bills" /> },
  { path: "feedback", element: <MmsPlaceholderPage title="Submit Feedback" /> },
  { path: "operations", element: <MmsPlaceholderPage title="Caretaker Operations" /> },
  { path: "windows", element: <MmsPlaceholderPage title="Registration Windows" /> },
  { path: "manage-menu", element: <MmsPlaceholderPage title="Manage Weekly Menu" /> },
  { path: "manage-bills", element: <MmsPlaceholderPage title="Billing Management" /> },
  { path: "operational-reports", element: <MmsPlaceholderPage title="Operational Reports" /> },
  { path: "oversight", element: <MmsPlaceholderPage title="Warden Oversight" /> },
  { path: "supervisory-reports", element: <MmsPlaceholderPage title="Supervisory Reports" /> },
  { path: "roles", element: <MmsPlaceholderPage title="Role Assignment" /> },
];
