"""The employee's own actions: apply, withdraw, replace a substitute, ask for a
cancellation, ask for an extension, report a resumption.

Nothing here edits a submitted request (BR-EL-034). A change is a new row with a
`parent`, which is what keeps the original approval intact and makes the
incremental-only posting rule for extensions (BR-EL-025) something the schema
says rather than something a developer has to remember.

Every function resolves the same three things before it moves anything: the
current configured policy, the rules, and the route. That order is deliberate —
BR-EL-030 says validation and routing use the CURRENT configuration, so the
policy is read once, at the top, and never cached across a request.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal

from core.api.exceptions import ConflictError, NotFoundError, ValidationError
from modules.directory import contracts as directory
from modules.leave.domain import categories as cat
from modules.leave.domain import routing
from modules.leave.domain.eligibility import Request as EligibilityRequest
from modules.leave.domain.eligibility import validate
from modules.leave.domain.guards import Facts
from modules.leave.domain.state_machine import (
    APPROVED,
    DRAFT,
    KIND_CANCELLATION,
    KIND_EXTENSION,
    KIND_NEW,
    KIND_RESUMPTION,
)
from modules.leave.models import LeavePolicy, LeaveRequest, OrganizationalUnit
from modules.leave.selectors import balances as balance_selectors
from modules.leave.selectors import leave as leave_selectors
from modules.leave.services import accounts, notifications, workflow

log = logging.getLogger("fusion.leave.applications")

P_CREATE = "leave.application.create"
P_WITHDRAW = "leave.application.withdraw"
P_CANCEL = "leave.application.cancel"
P_EXTEND = "leave.application.extend"
P_RESUMPTION = "leave.resumption.submit"


def _policy() -> LeavePolicy:
    policy = LeavePolicy.current()
    if policy is None:
        raise ValidationError(
            "Leave has not been configured yet — an administrator must save "
            "the leave policy first.", code="policy_missing")
    return policy


def _employee_kind(user_id: int) -> str:
    """What kind of employee this is, read through directory's contracts."""
    person = directory.get_users([user_id]).get(user_id)
    return person.kind if person else cat.STAFF


def _unit_head_for(department: str) -> int | None:
    unit = OrganizationalUnit.objects.filter(name__iexact=department).first()
    return unit.head_user_id if unit else None


def _department_of(user_id: int) -> str:
    person = directory.get_users([user_id]).get(user_id)
    return person.department if person else ""


def _active_intervals(user_id: int) -> tuple[cat.Interval, ...]:
    """The applicant's own pending or approved leave, which a new request may
    not impermissibly overlap (BR-EL-012)."""
    rows = (LeaveRequest.objects
            .filter(user_id=user_id, kind=KIND_NEW)
            .exclude(status__in=["rejected", "withdrawn", "cancelled"])
            .only("from_date", "to_date", "half"))
    return tuple(r.interval for r in rows)


def _validate(*, principal, category_code: str, start: date, end: date,
              half: str | None, substitute_user_id: int | None,
              substitute_required: bool, policy: LeavePolicy):
    """The rules, over real data (EL-UC-001 M4)."""
    user_id = principal.user_id
    cal = balance_selectors.effective_calendar(policy.year_label)
    verdict = validate(EligibilityRequest(
        category_code=category_code,
        employee_kind=_employee_kind(user_id),
        start=start, end=end, half=half or None,
        available=accounts.available(user_id, policy.year_label, category_code),
        closed_dates=cal["closed_dates"],
        restricted_holidays=cal["restricted_holidays"],
        vacation_periods=cal["vacation_periods"],
        existing=_active_intervals(user_id),
        substitute_required=substitute_required,
        substitute_user_id=substitute_user_id,
        applicant_user_id=user_id,
        substitute_intervals=_active_intervals(substitute_user_id or -1),
    ))
    if not verdict.is_valid:
        first = verdict.outcomes[0]
        raise ValidationError(
            first.message, code=first.code,
            details=[{"code": o.code, "message": o.message}
                     for o in verdict.outcomes])
    return verdict


def _route(*, category_code: str, principal, unit_head_user_id: int | None,
           policy: LeavePolicy) -> routing.Path:
    path = routing.resolve_path(category_code=category_code,
                                roles=tuple(principal.roles),
                                unit_head_user_id=unit_head_user_id,
                                hierarchy=policy.hierarchy)
    if not path.self_sanction and path.unit_head_user_id is None:
        raise ConflictError(
            "No Unit Head is configured for your unit, so this leave cannot "
            "be routed.", code="unit_head_missing")
    return path


def _facts_for(*, request: LeaveRequest, kind: str, substitute_required: bool,
               establishment_configured: bool, decision: str = "",
               leave_started: bool = False, leave_ended: bool = False,
               replacement_eligible: bool = False,
               routing_context_valid: bool = True) -> Facts:
    return Facts(
        kind=kind, category_code=request.category,
        employee_kind=_employee_kind(request.user_id),
        roles=tuple(request.applicant_roles or ()),
        substitute_required=substitute_required, decision=decision,
        establishment_configured=establishment_configured,
        leave_started=leave_started, leave_ended=leave_ended,
        replacement_eligible=replacement_eligible,
        routing_context_valid=routing_context_valid)


def apply(*, principal, category_code: str, start: date, end: date,
          half: str | None, purpose: str, station_leave_required: bool,
          station_leave_details: str, substitute_user_id: int | None,
          substitute_required: bool) -> LeaveRequest:
    """EL-UC-001. Validate, resolve the route, submit.

    The request is created in DRAFT and immediately moved through the table, so
    there is exactly one code path that decides where a submitted request lands
    — and the Director/higher-sanction question is answered by the guards, not
    by an `if` here.
    """
    policy = _policy()
    if category_code not in cat.CATEGORIES:
        raise ValidationError(
            f"{category_code or 'No category'} is not a leave category.",
            code="category_not_supported")

    verdict = _validate(principal=principal, category_code=category_code,
                        start=start, end=end, half=half,
                        substitute_user_id=substitute_user_id,
                        substitute_required=substitute_required, policy=policy)

    path = _route(category_code=category_code, principal=principal,
                  unit_head_user_id=_unit_head_for(_department_of(principal.user_id)),
                  policy=policy)

    request = LeaveRequest.objects.create(
        kind=KIND_NEW, category=category_code, user_id=principal.user_id,
        from_date=start, to_date=end, half=half or "", days=verdict.days,
        purpose=purpose, station_leave_required=station_leave_required,
        station_leave_details=station_leave_details,
        substitute_user_id=substitute_user_id,
        applicant_roles=list(principal.roles),
        unit_head_user_id=path.unit_head_user_id,
        final_authority=path.final_authority,
        establishment_first=path.establishment_first,
        self_sanction=path.self_sanction, status=DRAFT)

    workflow.move(
        request=request, principal=principal, permission=P_CREATE,
        facts=_facts_for(request=request, kind=KIND_NEW,
                         substitute_required=substitute_required,
                         establishment_configured=path.establishment_first),
        policy=policy)

    if request.status == "awaiting_substitute" and substitute_user_id:
        notifications.notify(
            topic="leave.substitute_requested",
            dedupe_key=f"leave.substitute:{request.pk}",
            recipient_user_id=substitute_user_id,
            subject="You have been nominated as a substitute",
            body=(f"{principal.display_name} has nominated you to hold "
                  f"responsibility during their {request.get_category_display()}."),
            request=request)
    return request


def _own_pending(principal, request_id: int, *, kinds: tuple[str, ...]) -> LeaveRequest:
    request = leave_selectors.my_request_by_id(principal, request_id)
    if request is None:
        raise NotFoundError("No such leave request.", code="not_found")
    if request.kind not in kinds:
        raise ConflictError("That action does not apply to this request.",
                            code="wrong_kind")
    if not request.is_pending:
        raise ConflictError(
            f"This request is {request.status.replace('_', ' ')} and can no "
            f"longer be changed.", code="not_pending")
    return request


def withdraw(*, principal, request_id: int, reason: str = "") -> LeaveRequest:
    """EL-UC-007. Immediate, terminal, and it stops everything downstream."""
    policy = _policy()
    request = _own_pending(principal, request_id,
                           kinds=(KIND_NEW, KIND_EXTENSION, KIND_CANCELLATION))
    workflow.move(
        request=request, principal=principal, permission=P_WITHDRAW,
        facts=_facts_for(request=request, kind=request.kind,
                         substitute_required=False,
                         establishment_configured=request.establishment_first,
                         decision=""),
        remarks=reason, policy=policy)
    notifications.tell_concerned_roles(
        request, "A leave request you were processing has been withdrawn")
    return request


def nominate_replacement(*, principal, request_id: int,
                          substitute_user_id: int) -> LeaveRequest:
    """EL-UC-019. A decline leaves the gate closed; replacing the nominee is the
    recovery, and a fresh response is then awaited."""
    policy = _policy()
    request = _own_pending(principal, request_id, kinds=(KIND_NEW, KIND_EXTENSION))
    if request.status != "applicant_action_required":
        raise ConflictError(
            "A replacement can only be nominated after a decline.",
            code="not_awaiting_replacement")

    _validate(principal=principal,
              category_code=request.category,
              start=request.from_date, end=request.to_date,
              half=request.half or None,
              substitute_user_id=substitute_user_id,
              substitute_required=True, policy=policy)
    request.substitute_user_id = substitute_user_id
    request.substitute_response = ""
    request.save(update_fields=["substitute_user_id", "substitute_response",
                                "updated_at"])

    workflow.move(
        request=request, principal=principal, permission="leave.substitute.nominate",
        facts=_facts_for(request=request, kind=request.kind,
                         substitute_required=True,
                         establishment_configured=request.establishment_first,
                         replacement_eligible=True),
        policy=policy)
    notifications.notify(
        topic="leave.substitute_requested",
        dedupe_key=f"leave.substitute:{request.pk}:{substitute_user_id}",
        recipient_user_id=substitute_user_id,
        subject="You have been nominated as a substitute",
        body=(f"{principal.display_name} has nominated you to hold "
              f"responsibility during their {request.get_category_display()}."),
        request=request)
    return request


def _approved_leave(principal, leave_id: int) -> LeaveRequest:
    leave = leave_selectors.my_request_by_id(principal, leave_id)
    if leave is None:
        raise NotFoundError("No such leave.", code="not_found")
    if leave.kind != KIND_NEW or leave.status != APPROVED:
        raise ConflictError("That leave is not an approved leave.",
                            code="not_approved")
    return leave


def request_cancellation(*, principal, leave_id: int,
                         reason: str) -> LeaveRequest:
    """EL-UC-008. Before the start date only, through the same hierarchy, and
    without touching the approved leave."""
    policy = _policy()
    leave = _approved_leave(principal, leave_id)
    if leave.from_date <= date.today():
        raise ConflictError(
            "This leave has already begun, so it can no longer be cancelled — "
            "an extension or a resumption applies instead.", code="leave_started")

    request = LeaveRequest.objects.create(
        kind=KIND_CANCELLATION, category=leave.category,
        user_id=principal.user_id, from_date=leave.from_date, to_date=leave.to_date,
        half=leave.half, days=Decimal("0"), purpose=reason, parent=leave,
        substitute_user_id=leave.substitute_user_id,
        applicant_roles=list(leave.applicant_roles),
        unit_head_user_id=leave.unit_head_user_id,
        final_authority=leave.final_authority,
        establishment_first=leave.establishment_first,
        self_sanction=leave.self_sanction, status=DRAFT)

    workflow.move(
        request=request, principal=principal, permission=P_CANCEL,
        facts=_facts_for(request=request, kind=KIND_CANCELLATION,
                         substitute_required=False,
                         establishment_configured=request.establishment_first,
                         leave_started=False),
        remarks=reason, policy=policy)
    return request


def request_extension(*, principal, leave_id: int, end_date: date,
                       substitute_user_id: int | None,
                       substitute_required: bool) -> LeaveRequest:
    """EL-UC-009. Only the incremental period is requested; the approved leave
    stays exactly as it was sanctioned until — and unless — this is approved."""
    policy = _policy()
    leave = _approved_leave(principal, leave_id)
    if not cat.category(leave.category).extension_eligible:
        raise ConflictError(
            f"{leave.get_category_display()} cannot be extended.",
            code="not_extendable")
    if not (leave.from_date <= date.today() <= leave.to_date):
        raise ConflictError(
            "An extension applies to leave currently in effect.",
            code="leave_not_ongoing")
    if end_date <= leave.to_date:
        raise ValidationError(
            "An extension must ask for a date after the approved end date.",
            code="extension_not_incremental")

    additional_from = leave.to_date + timedelta(days=1)
    verdict = _validate(principal=principal, category_code=leave.category,
                        start=additional_from, end=end_date, half=None,
                        substitute_user_id=substitute_user_id,
                        substitute_required=substitute_required, policy=policy)

    request = LeaveRequest.objects.create(
        kind=KIND_EXTENSION, category=leave.category, user_id=principal.user_id,
        from_date=additional_from, to_date=end_date, days=verdict.days,
        purpose=f"Extension of {leave.get_category_display()} ending "
                f"{leave.to_date}",
        station_leave_required=leave.station_leave_required,
        station_leave_details=leave.station_leave_details,
        substitute_user_id=substitute_user_id, parent=leave,
        applicant_roles=list(leave.applicant_roles),
        unit_head_user_id=leave.unit_head_user_id,
        final_authority=leave.final_authority,
        establishment_first=leave.establishment_first,
        self_sanction=leave.self_sanction, status=DRAFT)

    workflow.move(
        request=request, principal=principal, permission=P_EXTEND,
        facts=_facts_for(request=request, kind=KIND_EXTENSION,
                         substitute_required=substitute_required,
                         establishment_configured=request.establishment_first,
                         leave_started=True, leave_ended=False),
        policy=policy)

    if request.status == "awaiting_substitute" and substitute_user_id:
        notifications.notify(
            topic="leave.substitute_requested",
            dedupe_key=f"leave.substitute:{request.pk}",
            recipient_user_id=substitute_user_id,
            subject="You have been nominated as a substitute",
            body=(f"{principal.display_name} has nominated you to hold "
                  f"responsibility during the extension of their "
                  f"{request.get_category_display()}."),
            request=request)
    return request


def submit_resumption(*, principal, leave_id: int, actual_date: date,
                      remarks: str) -> LeaveRequest:
    """EL-UC-010. The employee reports the actual return; review is a separate
    act by the authority (EL-UC-011)."""
    policy = _policy()
    leave = _approved_leave(principal, leave_id)
    if not cat.category(leave.category).resumption_applies:
        raise ConflictError(
            "Resumption is recorded for EL, COL and VL.",
            code="resumption_not_applicable")
    if leave.from_date > actual_date:
        raise ValidationError(
            "The resumption date cannot be before the leave began.",
            code="resumption_before_leave")

    request = LeaveRequest.objects.create(
        kind=KIND_RESUMPTION, category=leave.category, user_id=principal.user_id,
        from_date=actual_date, to_date=actual_date, days=Decimal("0"),
        purpose=remarks, parent=leave,
        applicant_roles=list(leave.applicant_roles),
        unit_head_user_id=leave.unit_head_user_id,
        final_authority=leave.final_authority,
        establishment_first=leave.establishment_first,
        self_sanction=leave.self_sanction, status=DRAFT)

    workflow.move(
        request=request, principal=principal, permission=P_RESUMPTION,
        facts=_facts_for(request=request, kind=KIND_RESUMPTION,
                         substitute_required=False,
                         establishment_configured=False, leave_started=True),
        remarks=remarks, policy=policy)
    return request
