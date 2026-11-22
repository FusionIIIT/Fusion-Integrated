import { lazy, type ReactNode } from "react";
import { Navigate, type RouteObject } from "react-router-dom";
import { RequirePermission } from "../../auth/RequirePermission";

const ClubsPage = lazy(() => import("./pages/ClubsPage"));
const PollsPage = lazy(() => import("./pages/PollsPage"));

function guarded(permission: string, page: ReactNode) {
  return <RequirePermission permission={permission}>{page}</RequirePermission>;
}

export const routes: RouteObject[] = [
  { index: true, element: <Navigate to="clubs" replace /> },
  { path: "clubs", element: guarded("gymkhana.club.view", <ClubsPage />) },
  { path: "polls", element: guarded("gymkhana.poll.vote", <PollsPage />) },
];
