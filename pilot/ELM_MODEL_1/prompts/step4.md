Context (the same for every step): we are implementing the Employee Leave Management (ELM) module as an integrated module of this Fusion ERP repository (Django 5 + DRF backend under modules/, React 18 + Mantine 7 client under client/). Reuse Fusion's existing login, role mechanism, layout and backend structure; do not rebuild them.

Repository rules you must follow:
- There is no user table in this repository. The logged-in person is request.principal (fusion_auth.principal.Principal: user_id, username, kind, roles, permissions). Store people as integer ids (models.IntegerField), never as a ForeignKey to a user model.
- A module copies the shape of modules/placement: apps.py, registry.py, models.py, domain/ (pure Python, no Django imports), services/ (all writes), api/ (serializers, views, urls).
- The module code is "leave", and every permission code starts with "leave.".
- Every API view sets permission_classes = [HasModuleGrant("leave"), HasPermission("leave.<action>")], imported from fusion_auth.permissions.

Files marked read-only are context only. Write every file you create or change in full. Do not ask for more files; work with what is shown.

Step 4 of 7 — withdrawal, cancellation, extension, resumption and inquiry, from the read-only use cases EL-UC-007..013, with modules/leave/models.py and modules/leave/services/applications.py read-only.

Create modules/leave/services/lifecycle.py with these functions (each in transaction.atomic, appending a history row, raising ValueError when not allowed): withdraw_pending_request, request_cancellation (only before the leave starts), decide_cancellation (restore the balance when approved), request_extension (EL/COL/VL only, for ongoing leave), submit_resumption, review_resumption (adjust the balance for early or late return), get_balances(user_id, year) and get_history(user_id).
