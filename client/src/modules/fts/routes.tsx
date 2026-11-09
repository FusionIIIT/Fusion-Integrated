import { lazy, Suspense } from "react";
import { Navigate, type RouteObject } from "react-router-dom";

import FtsLayout from "./components/FtsLayout";

/** One lazy chunk per page; the import() arguments must stay static literals. */
const InboxPage = lazy(() => import("./pages/InboxPage"));
const OutboxPage = lazy(() => import("./pages/OutboxPage"));
const DraftsPage = lazy(() => import("./pages/DraftsPage"));
const CreateFilePage = lazy(() => import("./pages/CreateFilePage"));
const FileDetailPage = lazy(() => import("./pages/FileDetailPage"));

const wrap = (page: React.ReactNode) => (
  <Suspense fallback={null}>{page}</Suspense>
);

/** Relative paths: the shell mounts them under the manifest's basePath (/fts). */
export const routes: RouteObject[] = [
  {
    element: <FtsLayout />,
    children: [
      { index: true, element: <Navigate to="inbox" replace /> },
      { path: "inbox", element: wrap(<InboxPage />) },
      { path: "outbox", element: wrap(<OutboxPage />) },
      { path: "drafts", element: wrap(<DraftsPage />) },
      { path: "new", element: wrap(<CreateFilePage />) },
      { path: "files/:id", element: wrap(<FileDetailPage />) },
    ],
  },
];
