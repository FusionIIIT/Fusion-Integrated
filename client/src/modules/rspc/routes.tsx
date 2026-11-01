import { lazy } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

// Placeholder lazy routes for RSPC client module to satisfy routing validation
const DummyPage = lazy(() => Promise.resolve({ default: () => <div>RSPC</div> }));

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="portfolio" replace /> },
  { path: "portfolio", element: <DummyPage /> },
  { path: "proposals", element: <DummyPage /> },
  { path: "consultancy", element: <DummyPage /> },
  { path: "approvals", element: <DummyPage /> },
  { path: "reports", element: <DummyPage /> },
  { path: "notifications", element: <DummyPage /> },
];
