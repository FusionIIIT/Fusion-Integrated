import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

const PlaceholderPage = lazy(() => import("./pages/PlaceholderPage"));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="mine" replace /> },
  { path: "apply", element: <PlaceholderPage title="Apply for Leave" /> },
  { path: "mine", element: <PlaceholderPage title="My Leaves" /> },
  { path: "substitute", element: <PlaceholderPage title="Substitute Requests" /> },
  { path: "unit-head", element: <PlaceholderPage title="Unit Head Approvals" /> },
  { path: "establishment", element: <PlaceholderPage title="Establishment Routing" /> },
  { path: "sanctions", element: <PlaceholderPage title="Sanction Decisions" /> },
  { path: "admin", element: <PlaceholderPage title="Leave Administration" /> },
];
