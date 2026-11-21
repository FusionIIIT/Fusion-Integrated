Context (the same for every step): we are implementing the Patent Management System (PMS) module as an integrated module of this Fusion ERP repository (Django 5 + DRF backend under modules/, React 18 + Mantine 7 client under client/). Reuse Fusion's existing login, role mechanism, layout and backend structure; do not rebuild them.

Repository rules you must follow:
- There is no user table in this repository. The logged-in person is request.principal (fusion_auth.principal.Principal: user_id, username, kind, roles, permissions). Store people as integer ids (models.IntegerField), never as a ForeignKey to a user model.
- A module copies the shape of modules/placement: apps.py, registry.py, models.py, domain/ (pure Python, no Django imports), services/ (all writes), api/ (serializers, views, urls).
- The module code is "patent", and every permission code starts with "patent.".
- Every API view sets permission_classes = [HasModuleGrant("patent"), HasPermission("patent.<action>")], imported from fusion_auth.permissions.
- The four PMS actors are Applicant, Director, PCC_ADMIN and Attorney.

Files marked read-only are context only. Write every file you create or change in full. Do not ask for more files; work with what is shown.

Step 1 of 11 — module foundation, from the read-only problem statement and state table.

Create these files:
1. modules/patent/__init__.py — empty.
2. modules/patent/apps.py — PatentConfig with name "modules.patent" and label "patent", following modules/placement/apps.py.
3. modules/patent/registry.py — following modules/placement/registry.py: MODULE (code "patent", label "Patent Management", base_path "/patent"), NAV_ITEMS whose "to" paths are /patent/mine, /patent/submit, /patent/review, /patent/admin and /patent/attorney, PERMISSIONS (every code starts with "patent."), and ROLE_GRANTS keyed by the four actors (Applicant, Director, PCC_ADMIN, Attorney). Every permission must be granted to at least one role.
4. modules/patent/models.py — Django models on core.db.mixins.TimeStampedModel. People are integer user ids.
   - PatentApplication: unique application number, title, abstract, description, claims, technical domain, applicant_id, status, assigned_director_id, assigned_attorney_id, review_due_date, resubmission_deadline, latest decision and justification, version number. Status choices: Draft, Submitted, Under Review, Needs Revision, Resubmitted, Rejected, Appeal Submitted, Approved, Attorney Assigned, Filed, Granted, Withdrawn, Expired.
   - Inventor (application, optional user_id, name, email, contribution percent, agreement_signed).
   - ApplicationDocument (application, file name, content type, size in bytes, version, sensitivity, uploaded_by, archived).
   - AttorneyAssignment (application, attorney_id, status Offered/Accepted/Declined, decline reason).
   - PatentabilityOpinion (application, attorney_id, novelty, non-obviousness, utility, recommendation File Patent/Do Not File/Needs Amendment, opinion text).
   - Budget (application, filing fee, attorney fee, administrative cost, total, status Pending/Approved/Rejected/Escalated, decided_by, justification).
   - Filing (application, patent office, filing number, filing date, international flag, grant number, grant date).
   - OfficeAction (application, received date, response due date, description, response text, status Recorded/Awaiting Applicant Approval/Applicant Approved/Response Ready/Response Submitted).
   - MaintenanceRecord (application, due date, fee, decision Renewal Requested/Renew/Do Not Renew, decided_by).
   - Appeal (application, grounds, status Submitted/Remanded for Amendment/Rejection Upheld/Decision Modified, decided_by, justification).
   - ApplicationHistory: append-only row (application, actor_id, action, from_status, to_status, note).
