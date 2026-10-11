Context (the same for every step): we are implementing the Employee Leave Management (ELM) module as an integrated module of this Fusion ERP repository (Django 5 + DRF backend under modules/, React 18 + Mantine 7 client under client/). Reuse Fusion's existing login, role mechanism, layout and backend structure; do not rebuild them.

Repository rules you must follow:
- There is no user table in this repository. The logged-in person is request.principal (fusion_auth.principal.Principal: user_id, username, kind, roles, permissions). Store people as integer ids (models.IntegerField), never as a ForeignKey to a user model.
- A module copies the shape of modules/placement: apps.py, registry.py, models.py, domain/ (pure Python, no Django imports), services/ (all writes), api/ (serializers, views, urls).
- The module code is "leave", and every permission code starts with "leave.".
- Every API view sets permission_classes = [HasModuleGrant("leave"), HasPermission("leave.<action>")], imported from fusion_auth.permissions.

Files marked read-only are context only. Write every file you create or change in full. Do not ask for more files; work with what is shown.

Step 2 of 7 — leave policy rules, from the read-only business rules BR-EL-001..015 and modules/leave/models.py.

Create these files:
1. modules/leave/domain/__init__.py — empty.
2. modules/leave/domain/policy.py — pure Python (no Django, DRF or Celery imports): yearly entitlement per category and employee kind (faculty or staff), carry-forward rules, leave-day counting (continuous counting for EL/COL/VL; not for CL/SCL/RH), half-day CL counted as 0.5 day, the applicant non-overlap check with the half-day CL exception, substitute eligibility, and which categories the Unit Head decides finally (CL/RH) versus only recommends (SCL/EL/COL/VL). Use plain functions and dataclasses, with a one-line comment citing the BR-EL id where each rule is enforced.
