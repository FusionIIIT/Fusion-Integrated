Context (the same for every step): we are implementing the Employee Leave Management (ELM) module as an integrated module of this Fusion ERP repository (Django 5 + DRF backend under modules/, React 18 + Mantine 7 client under client/). Reuse Fusion's existing login, role mechanism, layout and backend structure; do not rebuild them.

Repository rules you must follow:
- There is no user table in this repository. The logged-in person is request.principal (fusion_auth.principal.Principal: user_id, username, kind, roles, permissions). Store people as integer ids (models.IntegerField), never as a ForeignKey to a user model.
- A module copies the shape of modules/placement: apps.py, registry.py, models.py, domain/ (pure Python, no Django imports), services/ (all writes), api/ (serializers, views, urls).
- The module code is "leave", and every permission code starts with "leave.".
- Every API view sets permission_classes = [HasModuleGrant("leave"), HasPermission("leave.<action>")], imported from fusion_auth.permissions.

Files marked read-only are context only. Write every file you create or change in full. Do not ask for more files; work with what is shown.

Step 5 of 7 — REST API. Read-only: fusion_auth/permissions.py, modules/leave/registry.py, modules/leave/models.py, modules/leave/services/applications.py, modules/leave/services/lifecycle.py.

Create these files:
1. modules/leave/api/__init__.py — empty.
2. modules/leave/api/serializers.py — DRF serializers for the leave application, balance and history models, plus input serializers for the apply and decision actions.
3. modules/leave/api/views.py — DRF APIView classes that call the service functions with request.principal.user_id. Every view sets permission_classes = [HasModuleGrant("leave"), HasPermission(<a permission declared in registry.py>)]. List views filter by the caller in the queryset (own applications, or applications waiting for the caller's decision), never by fetching and then checking. Turn ValueError into a 400 response.
4. modules/leave/api/urls.py — urlpatterns for: my applications (GET list, POST apply), application detail, withdraw, cancel, extend, resume, substitute respond, approvals inbox, decide, balances, history.
