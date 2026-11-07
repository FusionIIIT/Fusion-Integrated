Context (the same for every step): we are implementing the Patent Management System (PMS) module as an integrated module of this Fusion ERP repository (Django 5 + DRF backend under modules/, React 18 + Mantine 7 client under client/). Reuse Fusion's existing login, role mechanism, layout and backend structure; do not rebuild them.

Repository rules you must follow:
- There is no user table in this repository. The logged-in person is request.principal (fusion_auth.principal.Principal: user_id, username, kind, roles, permissions). Store people as integer ids (models.IntegerField), never as a ForeignKey to a user model.
- A module copies the shape of modules/placement: apps.py, registry.py, models.py, domain/ (pure Python, no Django imports), services/ (all writes), api/ (serializers, views, urls).
- The module code is "patent", and every permission code starts with "patent.".
- Every API view sets permission_classes = [HasModuleGrant("patent"), HasPermission("patent.<action>")], imported from fusion_auth.permissions.
- The four PMS actors are Applicant, Director, PCC_ADMIN and Attorney.

Files marked read-only are context only. Write every file you create or change in full. Do not ask for more files; work with what is shown.

Step 6 of 11 — REST API, part 1. Read-only: fusion_auth/permissions.py, modules/patent/registry.py, modules/patent/models.py, modules/patent/services/applications.py.

Create these files:
1. modules/patent/api/__init__.py — empty.
2. modules/patent/api/serializers.py — DRF serializers for every model in models.py, plus input serializers for submit, assign director, review decision, resubmit, withdraw, appeal and appeal decision.
3. modules/patent/api/views.py — DRF APIView classes that call the services in applications.py with request.principal.user_id: my applications (GET list, POST submit), application detail, history, assign director, review decision, review inbox (applications assigned to me), resubmit, withdraw, file appeal, decide appeal, and an admin list of submitted applications. Every view sets permission_classes = [HasModuleGrant("patent"), HasPermission(<a permission declared in registry.py>)]. List views filter by the caller in the queryset, never by fetching and then checking. Turn ValueError into a 400 response.
