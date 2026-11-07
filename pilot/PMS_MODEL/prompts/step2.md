Context (the same for every step): we are implementing the Patent Management System (PMS) module as an integrated module of this Fusion ERP repository (Django 5 + DRF backend under modules/, React 18 + Mantine 7 client under client/). Reuse Fusion's existing login, role mechanism, layout and backend structure; do not rebuild them.

Repository rules you must follow:
- There is no user table in this repository. The logged-in person is request.principal (fusion_auth.principal.Principal: user_id, username, kind, roles, permissions). Store people as integer ids (models.IntegerField), never as a ForeignKey to a user model.
- A module copies the shape of modules/placement: apps.py, registry.py, models.py, domain/ (pure Python, no Django imports), services/ (all writes), api/ (serializers, views, urls).
- The module code is "patent", and every permission code starts with "patent.".
- Every API view sets permission_classes = [HasModuleGrant("patent"), HasPermission("patent.<action>")], imported from fusion_auth.permissions.
- The four PMS actors are Applicant, Director, PCC_ADMIN and Attorney.

Files marked read-only are context only. Write every file you create or change in full. Do not ask for more files; work with what is shown.

Step 2 of 11 — PMS policy rules, from the read-only core business rules and state table, with modules/patent/models.py read-only.

Create these files:
1. modules/patent/domain/__init__.py — empty.
2. modules/patent/domain/policy.py — pure Python (no Django, DRF or Celery imports). Plain functions and dataclasses, each with a one-line comment citing the BR-PMS id it enforces:
   - ALLOWED_TRANSITIONS: a dict from each application status to the statuses it may move to (from the state table), and can_transition(from_status, to_status).
   - validate_document(file_name, content_type, size_bytes): PDF only and under 50 MB (BR-PMS-014, 015).
   - missing_required_fields(data): title, abstract, description, claims and at least one inventor (BR-PMS-017).
   - validate_justification(text): at least 50 characters (BR-PMS-030).
   - add_business_days(start_date, days) and review_due_date(assigned_on): 15 business days (BR-PMS-031).
   - resubmission_deadline(decision_date): 60 days (BR-PMS-035).
   - is_conflicted(reviewer_id, inventor_user_ids): a reviewer listed as inventor is conflicted (BR-PMS-025..027).
   - can_withdraw(status): only pre-filing statuses.
   - budget_needs_escalation(total, threshold).
