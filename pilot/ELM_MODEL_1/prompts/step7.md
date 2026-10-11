Context (the same for every step): we are implementing the Employee Leave Management (ELM) module as an integrated module of this Fusion ERP repository (Django 5 + DRF backend under modules/, React 18 + Mantine 7 client under client/). Reuse Fusion's existing login, role mechanism, layout and backend structure; do not rebuild them.

Repository rules you must follow:
- There is no user table in this repository. The logged-in person is request.principal (fusion_auth.principal.Principal: user_id, username, kind, roles, permissions). Store people as integer ids (models.IntegerField), never as a ForeignKey to a user model.
- A module copies the shape of modules/placement: apps.py, registry.py, models.py, domain/ (pure Python, no Django imports), services/ (all writes), api/ (serializers, views, urls).
- The module code is "leave", and every permission code starts with "leave.".
- Every API view sets permission_classes = [HasModuleGrant("leave"), HasPermission("leave.<action>")], imported from fusion_auth.permissions.

Files marked read-only are context only. Write every file you create or change in full. Do not ask for more files; work with what is shown.

Step 7a of 7 — client module wiring. Read-only: client/src/modules/placement/routes.tsx, client/src/lib/http.ts, modules/leave/registry.py, modules/leave/api/urls.py.

Create or change these files:
1. client/src/modules/leave/api.ts — TypeScript types and @tanstack/react-query hooks that call the leave endpoints through the shared `http` axios instance exported by client/src/lib/http.ts (its base URL is already /api/v1, so paths start with /leave/).
2. client/src/modules/leave/routes.tsx — lazy-loaded pages for the paths "apply", "mine", "approvals" and "substitute" (these must match the NAV_ITEMS "to" paths in registry.py), plus an index redirect to "mine", following placement/routes.tsx. The page files will be pages/ApplyLeavePage.tsx, pages/MyLeavesPage.tsx, pages/ApprovalsPage.tsx and pages/SubstituteRequestsPage.tsx.
3. client/src/app/registry.ts — add a "leave" entry (code "leave", basePath "/leave", load: () => import("../modules/leave/routes")) next to placement_cell. Keep everything else unchanged.
