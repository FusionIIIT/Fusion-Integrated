Context (the same for every step): we are implementing the Patent Management System (PMS) module as an integrated module of this Fusion ERP repository (Django 5 + DRF backend under modules/, React 18 + Mantine 7 client under client/). Reuse Fusion's existing login, role mechanism, layout and backend structure; do not rebuild them.

Repository rules you must follow:
- There is no user table in this repository. The logged-in person is request.principal (fusion_auth.principal.Principal: user_id, username, kind, roles, permissions). Store people as integer ids (models.IntegerField), never as a ForeignKey to a user model.
- A module copies the shape of modules/placement: apps.py, registry.py, models.py, domain/ (pure Python, no Django imports), services/ (all writes), api/ (serializers, views, urls).
- The module code is "patent", and every permission code starts with "patent.".
- Every API view sets permission_classes = [HasModuleGrant("patent"), HasPermission("patent.<action>")], imported from fusion_auth.permissions.
- The four PMS actors are Applicant, Director, PCC_ADMIN and Attorney.

Files marked read-only are context only. Write every file you create or change in full. Do not ask for more files; work with what is shown.

Step 5 of 11 — service layer after filing: office actions, grant and maintenance, from the read-only lifecycle use cases and business rules, with modules/patent/models.py read-only.

Create modules/patent/services/post_filing.py with these functions (each in transaction.atomic, appending an ApplicationHistory row, raising ValueError when not allowed):
record_office_action(attorney_id, application_id, received_date, response_due_date, description);
prepare_response(attorney_id, office_action_id, response_text, needs_applicant_approval) — Awaiting Applicant Approval or Response Ready;
approve_response(applicant_id, office_action_id) — only the owner; Applicant Approved;
submit_response(attorney_id, office_action_id) — only before the response due date; Response Submitted;
record_grant(attorney_id, application_id, grant_number, grant_date) — only for Filed applications; status Granted;
schedule_maintenance(attorney_id, application_id, due_date, fee) and decide_renewal(director_id, record_id, renew, justification) — only for Granted patents;
get_history(application_id) returning the history rows in order.
