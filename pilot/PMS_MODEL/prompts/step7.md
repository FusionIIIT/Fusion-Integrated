Context (the same for every step): we are implementing the Patent Management System (PMS) module as an integrated module of this Fusion ERP repository (Django 5 + DRF backend under modules/, React 18 + Mantine 7 client under client/). Reuse Fusion's existing login, role mechanism, layout and backend structure; do not rebuild them.

Repository rules you must follow:
- There is no user table in this repository. The logged-in person is request.principal (fusion_auth.principal.Principal: user_id, username, kind, roles, permissions). Store people as integer ids (models.IntegerField), never as a ForeignKey to a user model.
- A module copies the shape of modules/placement: apps.py, registry.py, models.py, domain/ (pure Python, no Django imports), services/ (all writes), api/ (serializers, views, urls).
- The module code is "patent", and every permission code starts with "patent.".
- Every API view sets permission_classes = [HasModuleGrant("patent"), HasPermission("patent.<action>")], imported from fusion_auth.permissions.
- The four PMS actors are Applicant, Director, PCC_ADMIN and Attorney.

Files marked read-only are context only. Write every file you create or change in full. Do not ask for more files; work with what is shown.

Step 7 of 11 — REST API, part 2. Read-only: fusion_auth/permissions.py, modules/patent/registry.py, modules/patent/api/serializers.py, modules/patent/api/views.py, modules/patent/services/legal.py, modules/patent/services/post_filing.py.

Create these files:
1. modules/patent/api/views_legal.py — APIView classes, written the same way as api/views.py, for: assign attorney, respond to assignment, my attorney assignments, record opinion, propose budget, decide budget, record filing, record office action, prepare response, approve response, submit response, record grant, schedule maintenance, decide renewal.
2. modules/patent/api/urls.py — urlpatterns for every view class in api/views.py and api/views_legal.py, using <int:pk> for ids.
