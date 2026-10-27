Context (the same for every step): we are implementing the Employee Leave Management (ELM) module as an integrated module of this Fusion ERP repository (Django 5 + DRF backend under modules/, React 18 + Mantine 7 client under client/). Reuse Fusion's existing login, role mechanism, layout and backend structure; do not rebuild them.

Repository rules you must follow:
- There is no user table in this repository. The logged-in person is request.principal (fusion_auth.principal.Principal: user_id, username, kind, roles, permissions). Store people as integer ids (models.IntegerField), never as a ForeignKey to a user model.
- A module copies the shape of modules/placement: apps.py, registry.py, models.py, domain/ (pure Python, no Django imports), services/ (all writes), api/ (serializers, views, urls).
- The module code is "leave", and every permission code starts with "leave.".
- Every API view sets permission_classes = [HasModuleGrant("leave"), HasPermission("leave.<action>")], imported from fusion_auth.permissions.

Files marked read-only are context only. Write every file you create or change in full. Do not ask for more files; work with what is shown.

Step 7b of 7 — client pages. Read-only: client/src/modules/placement/pages/MyApplicationsPage.tsx (the page pattern to follow), client/src/modules/leave/api.ts, client/src/modules/leave/routes.tsx.

Create these pages, each with a default export, reusing PageHeader, DataTable, StatusBadge and ErrorState from client/src/ui/components and Mantine 7 inputs:
1. client/src/modules/leave/pages/ApplyLeavePage.tsx — the leave application form (category, dates, CL half-day, purpose, Station Leave details, substitute user id).
2. client/src/modules/leave/pages/MyLeavesPage.tsx — my balances and my applications, with withdraw and cancel actions.
3. client/src/modules/leave/pages/ApprovalsPage.tsx — requests waiting for my decision, with approve, reject and recommend actions.
4. client/src/modules/leave/pages/SubstituteRequestsPage.tsx — substitute requests addressed to me, with accept and decline.
