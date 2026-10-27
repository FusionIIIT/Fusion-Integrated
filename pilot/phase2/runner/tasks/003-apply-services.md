TITLE: Rewrite application services (apply, substitute consent, withdraw)
FORMAT: whole
EDIT: modules/leave/services/applications.py modules/leave/services/__init__.py
READ: kit:phase2/DESIGN.md modules/leave/models.py modules/leave/domain/policy.py
LIMIT: 1500
POST: none
---
Review findings on the Phase-1 services: applications.py and lifecycle.py both define withdraw/cancel/extend/resumption functions (duplicated), they import modules.directory.models (other modules' internals are off limits) and fusion_auth.permissions (authorization belongs in the API), the overlap and substitute checks are placeholders, and no request is ever routed to a specific person.

Replace the whole content of modules/leave/services/applications.py with a clean implementation of the "Workflow" section of DESIGN.md for these functions only:

- class LeaveError(Exception); class NotFound(LeaveError)
- def log_action(app, actor_id: int, action: str, remark: str = "") -> None  (creates a LeaveAction)
- def get_balance(user_id: int, kind: str, category: str, year: int) -> LeaveBalance  (get_or_create; entitled = policy.entitlement(category, kind); raise LeaveError if not eligible)
- def has_overlap(user_id: int, start, end, half_day: str, exclude_id: int | None = None) -> bool  (checks that user's PENDING or APPROVED LEAVE-kind applications with policy.overlaps)
- def route_to_approver(app) -> None  (sets stage/assignee to UNIT_HEAD, or SANCTION when unit_head_id == user_id; self-sanction when there is no sanctioning authority)
- def apply_leave(user_id: int, kind: str, data: dict) -> LeaveApplication
- def respond_to_substitute(actor_id: int, application_id: int, accept: bool) -> LeaveApplication
- def replace_substitute(actor_id: int, application_id: int, substitute_id: int) -> LeaveApplication
- def withdraw(actor_id: int, application_id: int) -> LeaveApplication

apply_leave(data keys: category, start_date, end_date, half_day, purpose, station_leave, station_address, substitute_id) must, in order: check eligibility (policy.entitlement), compute days with policy.count_days (convert PolicyError to LeaveError), reject days <= 0, reject overlap with the applicant's own pending/approved leave (BR-EL-012), reject if get_balance(...).available < days, reject a substitute equal to the applicant or with overlapping pending/approved leave (BR-EL-014), load the applicant's ReportingLine (LeaveError "No reporting line configured" if missing), copy unit_head_id / establishment_id / sanctioning_authority_id onto the request, then set stage SUBSTITUTE with assignee = substitute (substitute_status PENDING) or call route_to_approver. Only the current assignee may respond as substitute; only the owner may replace a declined substitute or withdraw a PENDING request; otherwise raise NotFound. Wrap every write in transaction.atomic and call log_action for every change.

Replace modules/leave/services/__init__.py with just a one-line docstring (no imports).
Write both files in full. Do not ask for more files.
