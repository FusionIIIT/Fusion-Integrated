Context (the same for every step): we are implementing the Patent Management System (PMS) module as an integrated module of this Fusion ERP repository (Django 5 + DRF backend under modules/, React 18 + Mantine 7 client under client/). Reuse Fusion's existing login, role mechanism, layout and backend structure; do not rebuild them.

Repository rules you must follow:
- There is no user table in this repository. The logged-in person is request.principal (fusion_auth.principal.Principal: user_id, username, kind, roles, permissions). Store people as integer ids (models.IntegerField), never as a ForeignKey to a user model.
- A module copies the shape of modules/placement: apps.py, registry.py, models.py, domain/ (pure Python, no Django imports), services/ (all writes), api/ (serializers, views, urls).
- The module code is "patent", and every permission code starts with "patent.".
- Every API view sets permission_classes = [HasModuleGrant("patent"), HasPermission("patent.<action>")], imported from fusion_auth.permissions.
- The four PMS actors are Applicant, Director, PCC_ADMIN and Attorney.

Files marked read-only are context only. Write every file you create or change in full. Do not ask for more files; work with what is shown.

Step 9 of 11 — client module wiring. Read-only: client/src/modules/placement/routes.tsx, client/src/lib/http.ts, modules/patent/registry.py, modules/patent/api/urls.py.

Create or change these files:
1. client/src/modules/patent/api.ts — TypeScript types and @tanstack/react-query hooks that call the patent endpoints through the shared `http` axios instance exported by client/src/lib/http.ts (its base URL is already /api/v1, so paths start with /patent/).
2. client/src/modules/patent/routes.tsx — lazy-loaded pages for the paths "mine", "submit", "review", "admin" and "attorney" (these must match the NAV_ITEMS "to" paths in registry.py), plus an index redirect to "mine", following placement/routes.tsx. The page files will be pages/MyApplicationsPage.tsx, pages/SubmitApplicationPage.tsx, pages/ReviewPage.tsx, pages/AdminPage.tsx and pages/AttorneyPage.tsx.
3. client/src/app/registry.ts — add a "patent" entry (code "patent", basePath "/patent", load: () => import("../modules/patent/routes")) next to placement_cell. Keep everything else unchanged.
