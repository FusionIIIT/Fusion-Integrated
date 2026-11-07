Context (the same for every step): we are implementing the Patent Management System (PMS) module as an integrated module of this Fusion ERP repository (Django 5 + DRF backend under modules/, React 18 + Mantine 7 client under client/). Reuse Fusion's existing login, role mechanism, layout and backend structure; do not rebuild them.

Repository rules you must follow:
- There is no user table in this repository. The logged-in person is request.principal (fusion_auth.principal.Principal: user_id, username, kind, roles, permissions). Store people as integer ids (models.IntegerField), never as a ForeignKey to a user model.
- A module copies the shape of modules/placement: apps.py, registry.py, models.py, domain/ (pure Python, no Django imports), services/ (all writes), api/ (serializers, views, urls).
- The module code is "patent", and every permission code starts with "patent.".
- Every API view sets permission_classes = [HasModuleGrant("patent"), HasPermission("patent.<action>")], imported from fusion_auth.permissions.
- The four PMS actors are Applicant, Director, PCC_ADMIN and Attorney.

Files marked read-only are context only. Write every file you create or change in full. Do not ask for more files; work with what is shown.

Step 10 of 11 — client pages for the Applicant. Read-only: client/src/modules/placement/pages/MyApplicationsPage.tsx (the page pattern to follow), client/src/modules/patent/api.ts, client/src/modules/patent/routes.tsx.

Create these pages, each with a default export, reusing PageHeader, DataTable, StatusBadge and ErrorState from client/src/ui/components and Mantine 7 inputs:
1. client/src/modules/patent/pages/SubmitApplicationPage.tsx — the submission form (title, abstract, description, claims, technical domain, inventors with name, email and contribution percent).
2. client/src/modules/patent/pages/MyApplicationsPage.tsx — my applications with status, plus withdraw, resubmit, appeal and approve-office-action-response actions where the status allows them.
