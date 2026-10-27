Context (the same for every step): we are implementing the Employee Leave Management (ELM) module as an integrated module of this Fusion ERP repository (Django 5 + DRF backend under modules/, React 18 + Mantine 7 client under client/). Reuse Fusion's existing login, role mechanism, layout and backend structure; do not rebuild them.

Repository rules you must follow:
- There is no user table in this repository. The logged-in person is request.principal (fusion_auth.principal.Principal: user_id, username, kind, roles, permissions). Store people as integer ids (models.IntegerField), never as a ForeignKey to a user model.
- A module copies the shape of modules/placement: apps.py, registry.py, models.py, domain/ (pure Python, no Django imports), services/ (all writes), api/ (serializers, views, urls).
- The module code is "leave", and every permission code starts with "leave.".
- Every API view sets permission_classes = [HasModuleGrant("leave"), HasPermission("leave.<action>")], imported from fusion_auth.permissions.

Files marked read-only are context only. Write every file you create or change in full. Do not ask for more files; work with what is shown.

Step 3 of 7 — service layer for applying, substitute consent and decisions, from the read-only use cases EL-UC-001..005 and EL-UC-019 and business rules BR-EL-016..038, with modules/leave/models.py and modules/leave/domain/policy.py read-only.

Create these files:
1. modules/leave/services/__init__.py — empty.
2. modules/leave/services/applications.py — functions, each wrapped in transaction.atomic and appending an action-history row: apply_leave (validate with domain/policy.py, then route either to substitute consent or to the Unit Head), respond_to_substitute_request (accept or decline), nominate_replacement_substitute, unit_head_review (final decision for CL/RH; Recommended / Not Recommended for the other categories), establishment_verify_and_route, final_sanction_decision (approve or reject; deduct the balance on approval). Each function takes the acting user's id and raises ValueError with a clear message when the action is not allowed in the current status.
