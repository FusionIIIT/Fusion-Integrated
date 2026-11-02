import { Navigate, type RouteObject } from "react-router-dom";
import Placeholder from "./pages/Placeholder";

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "mine", element: <Placeholder title="My Applications" /> },
  { path: "submit", element: <Placeholder title="Submit Application" /> },
  { path: "queue", element: <Placeholder title="Application Queue" /> },
  { path: "reviews", element: <Placeholder title="Director Reviews" /> },
  { path: "filings", element: <Placeholder title="Patent Filings" /> },
  { path: "maintenance", element: <Placeholder title="Post-Grant Maintenance" /> },
  { path: "reports", element: <Placeholder title="Reports & Analytics" /> },
  { path: "my-reports", element: <Placeholder title="My Reports" /> },
  { path: "admin", element: <Placeholder title="PMS Administration" /> },
  { path: "audit", element: <Placeholder title="Audit Trail" /> },
];
