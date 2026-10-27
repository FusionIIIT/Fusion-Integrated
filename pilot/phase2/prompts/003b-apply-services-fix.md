Review of modules/leave/services/applications.py from task 003 found these defects (the file does not even import):
1. It imports names that do not exist in policy.py (calculate_consumed_days, check_applicant_overlap, requires_substitute, unit_head_decision_required, get_categories_requiring_unit_head_decision). policy.py only has: PolicyError, CATEGORIES, ENTITLEMENT, entitlement, count_days, overlaps, unit_head_is_final.
2. It calls policy functions through `PolicyError.__bases__[0].__subclasses__()[0]...`. Call them directly: policy.entitlement(...), policy.count_days(...), policy.overlaps(...).
3. apply_leave uses LeaveApplication.objects.get_or_create(user_id=...), which overwrites the applicant's previous application. Every apply must create a NEW row with LeaveApplication.objects.create(...), including kind=RequestKind.LEAVE and days.
4. `except Exception: continue` around the overlap checks swallows the LeaveError it raises, so overlaps are never rejected. Do not wrap the overlap checks in try/except.
5. A substitute is optional (DESIGN.md): there is no "requires substitute" rule. If data["substitute_id"] is not None: reject it when it equals the applicant, reject it when the substitute has a PENDING or APPROVED LEAVE-kind application of ANY category overlapping the dates, then set stage=Stage.SUBSTITUTE, assignee_id=substitute_id, substitute_status=SubstituteStatus.PENDING. Otherwise substitute_status=SubstituteStatus.NOT_REQUIRED and call route_to_approver(app).
6. route_to_approver uses LeaveCategory.SUBSTITUTE / SANCTION, which do not exist. Use Stage. Rule: if app.unit_head_id == app.user_id then stage=Stage.SANCTION and assignee_id = app.sanctioning_authority_id or app.user_id (self-sanction, BR-EL-020); else stage=Stage.UNIT_HEAD and assignee_id=app.unit_head_id. It must not look at substitutes.
7. respond_to_substitute sets status "approved" on accept. Correct: only when stage is SUBSTITUTE, status PENDING and assignee_id == actor_id (else NotFound). Accept: substitute_status=ACCEPTED then route_to_approver(app). Decline: substitute_status=DECLINED, assignee_id=None, status stays PENDING.
8. replace_substitute: only the owner, only while status is PENDING and substitute_status is DECLINED (else NotFound); validate the new substitute as in item 5; set substitute_id, substitute_status=PENDING, stage=Stage.SUBSTITUTE, assignee_id=new substitute.
9. withdraw: only the owner and only status PENDING (else NotFound); set status=Status.WITHDRAWN, assignee_id=None.
10. Status strings such as "submitted" do not exist. Use the TextChoices from models: Status.PENDING, Status.APPROVED, Status.WITHDRAWN, Stage.*, SubstituteStatus.*, RequestKind.LEAVE.
11. has_overlap must filter kind=RequestKind.LEAVE and status in (PENDING, APPROVED), not category__in.
12. Nothing is wrapped in transaction.atomic. Decorate apply_leave, respond_to_substitute, replace_substitute and withdraw with @transaction.atomic and load existing rows with LeaveApplication.objects.select_for_update().filter(id=application_id).first() (None -> NotFound).
13. Errors must reuse Fusion's platform errors so the API returns the standard envelope.

Start the file with exactly these imports and classes:

from django.db import transaction

from core.api.exceptions import BadRequestError, NotFoundError
from modules.leave.domain import policy
from modules.leave.models import (
    LeaveAction, LeaveApplication, LeaveBalance, ReportingLine,
    RequestKind, Stage, Status, SubstituteStatus,
)


class LeaveError(BadRequestError):
    code = "leave_error"


class NotFound(NotFoundError):
    pass

Keep the same function names and signatures as before (log_action, get_balance, has_overlap, route_to_approver, apply_leave, respond_to_substitute, replace_substitute, withdraw) and the apply_leave order from DESIGN.md: eligibility (policy.entitlement is None -> LeaveError), days (policy.PolicyError -> LeaveError), days <= 0, own overlap, balance (get_balance(...).available < days), substitute checks, ReportingLine (missing -> LeaveError("No reporting line configured.")), create, route. get_balance uses LeaveBalance.objects.get_or_create with defaults entitled and used 0. Call log_action for every change. Write the whole file. Do not ask for more files.
