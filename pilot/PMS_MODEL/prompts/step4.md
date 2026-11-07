Context (the same for every step): we are implementing the Patent Management System (PMS) module as an integrated module of this Fusion ERP repository (Django 5 + DRF backend under modules/, React 18 + Mantine 7 client under client/). Reuse Fusion's existing login, role mechanism, layout and backend structure; do not rebuild them.

Repository rules you must follow:
- There is no user table in this repository. The logged-in person is request.principal (fusion_auth.principal.Principal: user_id, username, kind, roles, permissions). Store people as integer ids (models.IntegerField), never as a ForeignKey to a user model.
- A module copies the shape of modules/placement: apps.py, registry.py, models.py, domain/ (pure Python, no Django imports), services/ (all writes), api/ (serializers, views, urls).
- The module code is "patent", and every permission code starts with "patent.".
- Every API view sets permission_classes = [HasModuleGrant("patent"), HasPermission("patent.<action>")], imported from fusion_auth.permissions.
- The four PMS actors are Applicant, Director, PCC_ADMIN and Attorney.

Files marked read-only are context only. Write every file you create or change in full. Do not ask for more files; work with what is shown.

Step 4 of 11 — service layer for attorney assignment, patentability assessment, budget and filing, from the read-only lifecycle use cases and business rules, with modules/patent/models.py and modules/patent/domain/policy.py read-only.

Create modules/patent/services/legal.py with these functions (each in transaction.atomic, appending an ApplicationHistory row, raising ValueError when not allowed):
assign_attorney(admin_id, application_id, attorney_id) — only for Approved applications; creates an Offered AttorneyAssignment;
respond_to_assignment(attorney_id, assignment_id, accept, reason) — accept sets the application to Attorney Assigned; decline records the reason and allows one reassignment;
record_opinion(attorney_id, application_id, novelty, non_obviousness, utility, recommendation, text) — only the assigned Attorney;
propose_budget(admin_id, application_id, filing_fee, attorney_fee, admin_cost) and decide_budget(director_id, budget_id, approve, justification, threshold) — escalate instead of approving when the total exceeds the threshold;
record_filing(attorney_id, application_id, office, filing_number, filing_date, international) — only when the budget is Approved and every inventor agreement is signed (BR-PMS-020); status Filed.
