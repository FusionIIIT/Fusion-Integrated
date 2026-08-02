import { Center, Loader } from "@mantine/core";
import { lazy, Suspense, useEffect, useState } from "react";
import { Navigate, Outlet, type RouteObject, useRoutes } from "react-router-dom";

import { useAuth } from "../auth/AuthProvider";
import { RequireAuth } from "../auth/RequireAuth";
import {
  RecruiterAuthProvider, RequireRecruiter,
} from "../recruiter/RecruiterAuth";
import { RecruiterNotFound, RecruiterShell } from "../recruiter/RecruiterShell";
import LoginPage from "./LoginPage";
import { MODULE_REGISTRY } from "./registry";
import { Dashboard, NotFound, Shell } from "./Shell";

// The recruiter portal is a separate audience with a separate credential, so
// none of it belongs in the bundle an institute user downloads.
const RecruiterLoginPage = lazy(() => import("../recruiter/RecruiterLoginPage"));
const AcceptInvitePage = lazy(() => import("../recruiter/AcceptInvitePage"));
const RecruiterPostings = lazy(
  () => import("../recruiter/pages/RecruiterPostingsPage"));
const RecruiterApplicants = lazy(
  () => import("../recruiter/pages/RecruiterApplicantsPage"));
const RecruiterInterviews = lazy(
  () => import("../recruiter/pages/RecruiterInterviewsPage"));

const loading = <Center h="60vh"><Loader /></Center>;

/** `/recruiter/*`, a sibling of the institute app rather than nested inside
 *  it: a recruiter never enters the institute AuthProvider, never fetches
 *  `/api/v1/me`, and a 401 lands on their own login. */
const recruiterRoutes: RouteObject = {
  path: "/recruiter",
  element: (
    <RecruiterAuthProvider>
      <Suspense fallback={loading}><Outlet /></Suspense>
    </RecruiterAuthProvider>
  ),
  children: [
    { path: "login", element: <RecruiterLoginPage /> },
    { path: "accept", element: <AcceptInvitePage /> },
    {
      path: "",
      element: <RequireRecruiter><RecruiterShell /></RequireRecruiter>,
      children: [
        { index: true, element: <Navigate to="postings" replace /> },
        { path: "postings", element: <RecruiterPostings /> },
        { path: "applicants", element: <RecruiterApplicants /> },
        { path: "interviews", element: <RecruiterInterviews /> },
        { path: "*", element: <RecruiterNotFound /> },
      ],
    },
  ],
};

/**
 * Resolve the route tables of every module the server granted.
 *
 * Loaded into state rather than via react-router's `lazy`, which only works
 * with a data router — under <BrowserRouter> + useRoutes it is silently
 * ignored and every module path falls through to NotFound. The dynamic
 * import() still produces one chunk per module.
 */
function useModuleRoutes(moduleCodes: string[]): {
  routes: RouteObject[];
  ready: boolean;
} {
  const [routes, setRoutes] = useState<RouteObject[]>([]);
  const [ready, setReady] = useState(false);
  const key = moduleCodes.join(",");

  useEffect(() => {
    let cancelled = false;
    const manifests = moduleCodes
      .map((code) => MODULE_REGISTRY[code])
      .filter((m): m is NonNullable<typeof m> => Boolean(m));

    if (!manifests.length) {
      setRoutes([]);
      setReady(true);
      return;
    }

    Promise.all(
      manifests.map(async (m) => ({
        path: m.basePath.replace(/^\//, ""),
        element: <Outlet />,
        children: (await m.load()).routes,
      })),
    ).then((loaded) => {
      if (cancelled) return;
      setRoutes(loaded);
      setReady(true);
    });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  return { routes, ready };
}

export function AppRoutes() {
  const { session } = useAuth();
  const { routes: moduleRoutes, ready } = useModuleRoutes(session?.modules ?? []);

  // Held back until the granted modules register, or a deep link flashes
  // NotFound before the real page.
  const authedChildren: RouteObject[] = [
    { index: true, element: <Dashboard /> },
    { path: "dashboard", element: <Dashboard /> },
    ...moduleRoutes,
    ...(ready
      ? [{ path: "*", element: <NotFound /> }]
      : [{ path: "*", element: <Center h="60vh"><Loader /></Center> }]),
  ];

  return useRoutes([
    { path: "/login", element: <LoginPage /> },
    // Matched before "/" so the institute RequireAuth never sees a recruiter.
    recruiterRoutes,
    {
      path: "/",
      element: (
        <RequireAuth>
          <Shell />
        </RequireAuth>
      ),
      children: authedChildren,
    },
  ]);
}
