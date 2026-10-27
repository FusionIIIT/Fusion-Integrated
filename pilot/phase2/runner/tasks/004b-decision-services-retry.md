TITLE: Rewrite decision and cancellation services (retry after the token-limit failure)
FORMAT: whole
EDIT: modules/leave/services/lifecycle.py
READ: kit:phase2/DESIGN.md modules/leave/models.py modules/leave/domain/policy.py modules/leave/services/applications.py
LIMIT: 1500
POST: none
---
Task 004 hit the output token limit while copying the old file, which has now been emptied. Write the new file from scratch; it should be about 150 lines.

Review findings: the Phase-1 lifecycle.py duplicates functions from applications.py, lets any caller decide any request (no check that the caller is the assigned approver), never adds approved days to the balance correctly, and creates cancellation records in a "draft" status that no one can act on.

Replace the whole content of modules/leave/services/lifecycle.py with these functions, following the "Workflow" section of DESIGN.md. Import LeaveError, NotFound, log_action and route_to_approver from modules.leave.services.applications (read-only) instead of redefining anything.

- def decide(actor_id: int, application_id: int, decision: str, remark: str = "") -> LeaveApplication
  Load the application with select_for_update; raise NotFound unless status is PENDING and assignee_id == actor_id.
  Stage UNIT_HEAD: if policy.unit_head_is_final(category) the decision must be "approve" or "reject" (BR-EL-016) and is final; otherwise it must be "recommended" or "not_recommended" (BR-EL-017), stored in unit_head_recommendation, then move to ESTABLISHMENT (assignee establishment_id) if establishment_id is set, else SANCTION (assignee sanctioning_authority_id, or the applicant for self-sanction).
  Stage ESTABLISHMENT: decision must be "verify"; move to SANCTION.
  Stage SANCTION: decision must be "approve" or "reject"; final.
  Any other decision raises LeaveError. Any other stage (for example SUBSTITUTE, while the substitute has not yet accepted) raises LeaveError("This request is not awaiting a decision.").
- def finalize(app, actor_id: int, approved: bool) -> None
  Sets status, stage DONE, assignee None, decided_at = timezone.now(). On approval of a LEAVE request add app.days to the used field of LeaveBalance.objects.select_for_update().get(user_id=app.user_id, year=app.start_date.year, category=app.category) (the row always exists because apply_leave created it); on approval of a CANCELLATION request set the parent to CANCELLED and subtract the parent's days from that same balance row (BR-EL-023). Rejection changes no balance.
- def request_cancellation(actor_id: int, application_id: int, today) -> LeaveApplication
  Only the owner, only an APPROVED LEAVE-kind request whose start_date is after today, and only if it has no PENDING cancellation; creates a CANCELLATION request copying category, dates, days and routing fields, parent = the leave, then calls route_to_approver.

Wrap writes in transaction.atomic and call log_action for every change. Write the whole file. Do not ask for more files.

Use exactly these imports at the top of lifecycle.py. They are the only names you need, and every one of them exists; do not import anything else (task 003 failed because it imported functions that do not exist):

from django.db import transaction
from django.utils import timezone

from modules.leave.domain import policy
from modules.leave.models import LeaveApplication, LeaveBalance, RequestKind, Stage, Status
from modules.leave.services.applications import LeaveError, NotFound, log_action, route_to_approver
