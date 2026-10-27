TITLE: Register the Reporting Lines page as a route and a sidebar item
FORMAT: diff
EDIT: client/src/modules/leave/routes.tsx modules/leave/registry.py
LIMIT: 900
POST: permissions
---
Wire the new ReportingLinesPage into the module. Fusion requires every sidebar item to have a client route and vice versa (ops/checks/nav_matches_routes.py). Fix only this, with SEARCH/REPLACE edits:

1. client/src/modules/leave/routes.tsx: after the line
const SubstituteRequestsPage = lazy(() => import("./pages/SubstituteRequestsPage"));
add
const ReportingLinesPage = lazy(() => import("./pages/ReportingLinesPage"));
and after the route entry `  { path: "substitute", element: <SubstituteRequestsPage /> },` add
  { path: "admin", element: <ReportingLinesPage /> },

2. modules/leave/registry.py: add a fifth entry at the end of NAV_ITEMS (after the leave.approvals entry, inside the list):
    {"code": "leave.admin", "label": "Reporting Lines", "icon": "Gear", "to": "/leave/admin", "required_permission": "leave.admin.manage", "sort_order": 30},
(keep the same dict style and line breaks as the other entries).

Do not change anything else.
