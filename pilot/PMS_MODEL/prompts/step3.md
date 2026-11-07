Context (the same for every step): we are implementing the Patent Management System (PMS) module as an integrated module of this Fusion ERP repository (Django 5 + DRF backend under modules/, React 18 + Mantine 7 client under client/). Reuse Fusion's existing login, role mechanism, layout and backend structure; do not rebuild them.

Repository rules you must follow:
- There is no user table in this repository. The logged-in person is request.principal (fusion_auth.principal.Principal: user_id, username, kind, roles, permissions). Store people as integer ids (models.IntegerField), never as a ForeignKey to a user model.
- A module copies the shape of modules/placement: apps.py, registry.py, models.py, domain/ (pure Python, no Django imports), services/ (all writes), api/ (serializers, views, urls).
- The module code is "patent", and every permission code starts with "patent.".
- Every API view sets permission_classes = [HasModuleGrant("patent"), HasPermission("patent.<action>")], imported from fusion_auth.permissions.
- The four PMS actors are Applicant, Director, PCC_ADMIN and Attorney.

Files marked read-only are context only. Write every file you create or change in full. Do not ask for more files; work with what is shown.

Step 3 of 11 — service layer for submission, Director assignment and review, revision, withdrawal and appeal, from the read-only use cases and core business rules, with modules/patent/models.py and modules/patent/domain/policy.py read-only.

Create these files:
1. modules/patent/services/__init__.py — empty.
2. modules/patent/services/applications.py — functions, each wrapped in transaction.atomic, checking the move with policy.can_transition and appending an ApplicationHistory row:
   submit_application(applicant_id, data, inventors, documents) — validate fields and documents, assign a unique application number, status Submitted;
   assign_director(admin_id, application_id, director_id) — refuse a conflicted Director, set review_due_date, status Under Review;
   review_application(director_id, application_id, decision, justification) — only the assigned Director; decision Approve, Reject or Needs Revision; justification of at least 50 characters; set resubmission_deadline for Reject/Needs Revision;
   resubmit_application(applicant_id, application_id, changes, response_to_feedback) — only the owner, only from Needs Revision or Rejected and before the deadline; bump the version; status Resubmitted;
   withdraw_application(applicant_id, application_id, reason) — only the owner and only when policy.can_withdraw;
   expire_overdue_resubmissions(today) — set Expired where the deadline has passed;
   file_appeal(applicant_id, application_id, grounds) and decide_appeal(director_id, appeal_id, outcome, justification).
   Each function takes the acting user's id and raises ValueError with a clear message when the action is not allowed.
