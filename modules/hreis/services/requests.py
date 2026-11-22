"""Employee HR request submission, validated against active institutional policy."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.hreis.domain import claims, leave, routing, workflow
from modules.hreis.models import (
    AppraisalDetail,
    ApprovalRouteStep,
    AuditEvent,
    ClaimDetail,
    EmployeeServiceRecord,
    HRRequest,
    HRRequestTransition,
    LeaveLedgerEntry,
    Notification,
    OutboxEvent,
)
from modules.hreis.services.authz import require
from modules.hreis.services.policies import current_policy

_EMPLOYEE_ROLES = frozenset({"faculty", "staff"})


def _employee_record(actor, permission: str) -> EmployeeServiceRecord:
    require(actor, permission, allowed_roles=_EMPLOYEE_ROLES)
    if getattr(actor, "kind", None) != actor.active_role:
        raise BadRequestError(
            "Select your current employee category.", code="employee_category_mismatch"
        )
    row = EmployeeServiceRecord.objects.filter(user_id=actor.user_id).first()
    if row is None:
        raise NotFoundError(
            "Your official service record is not yet available. Refresh your current HR view "
            "or contact HR for help.",
            code="employee_record_missing",
        )
    return row


def _key(key: str) -> str:
    if not isinstance(key, str) or not 1 <= len(key) <= 100 or not key.strip():
        raise BadRequestError("Provide a unique operation key.", code="missing_idempotency_key")
    if HRRequestTransition.objects.filter(idempotency_key=key).exists():
        raise ConflictError(
            "This request has already been submitted. Contact HR to resolve this before retrying.",
            code="operation_replayed",
        )
    return key


def _route(family: str, kind: str, department: str, policy) -> routing.ApprovalRoute:
    route_rows = policy.parameters.get("routes")
    if not isinstance(route_rows, list):
        raise ConflictError(
            "No approval routes are configured for this policy. Contact HR to resolve this "
            "before retrying.",
            code="policy_route_missing",
        )
    configured = {}
    for row in route_rows:
        route = routing.ApprovalRoute(
            family=family,
            employee_kind=row["employee_kind"],
            department=row["department"],
            version=f"{family}:{policy.version}",
            authorities=tuple(row["authorities"]),
        )
        configured[(family, route.employee_kind, route.department)] = route
    try:
        return routing.choose_route(family, kind, department, configured)
    except routing.RouteError as exc:
        raise ConflictError(str(exc), code=exc.code) from exc


def _freeze_route(row, route):
    for position, designation in enumerate(route.authorities):
        ApprovalRouteStep.objects.create(
            request=row,
            position=position,
            designation=designation,
            policy_version_label=route.version,
        )


def _submission_evidence(actor, row, transition, key, family, state):
    HRRequestTransition.objects.create(
        request=row,
        source=transition.source,
        event=transition.event,
        target=state,
        actor_user_id=actor.user_id,
        acting_designation=actor.active_role,
        specification=transition.specification,
        step_before=0,
        step_after=0,
        idempotency_key=key,
    )
    AuditEvent.objects.create(
        event_key=f"request:{key}",
        actor_user_id=actor.user_id,
        acting_designation=actor.active_role,
        subject_user_id=actor.user_id,
        action=f"{family}_submit",
        resource_kind="hr_request",
        resource_id=row.pk,
        data={"family": family, "state": state, "specification": transition.specification},
    )
    Notification.objects.create(
        recipient_user_id=actor.user_id,
        request=row,
        event_key=f"notification:{key}",
        title=f"{family.upper()} request submitted",
        message="Your HR request was recorded and is awaiting the next workflow step.",
    )
    OutboxEvent.objects.create(
        event_key=f"outbox:{key}",
        event_type="hreis.notification",
        payload={
            "request_id": row.pk,
            "subject_user_id": actor.user_id,
            "family": family,
            "state": state,
        },
    )


def _persist(
    actor,
    *,
    family: str,
    subtype: str,
    state: str,
    payload: dict,
    policy,
    transition,
    key: str,
    route=None,
    submitted_at=None,
) -> HRRequest:
    row = HRRequest.objects.create(
        user_id=actor.user_id,
        family=family,
        subtype=subtype,
        state=state,
        payload=payload,
        policy_version=policy,
        version=1,
        route_step=0,
        submitted_at=submitted_at or timezone.now(),
    )
    if route is not None:
        _freeze_route(row, route)
    _submission_evidence(actor, row, transition, key, family, state)
    return row


def _validated_leave(actor, policy, leave_type, duration, justification):
    eligibility = (
        policy.parameters.get("eligibility", {})
        .get(
            actor.kind,
            {},
        )
        .get(leave_type)
    )
    balance_entries = LeaveLedgerEntry.objects.filter(
        user_id=actor.user_id,
        leave_type=leave_type,
    ).values_list("quantity", flat=True)
    available = leave.ledger_balance(balance_entries)
    try:
        valid = leave.validate_submission(
            leave_type,
            duration,
            justification,
            available_balance=available,
            is_eligible=eligibility,
        )
    except leave.InvalidLeaveRequest as exc:
        raise ConflictError(str(exc), code=exc.code) from exc
    return valid


@transaction.atomic
def submit_leave(
    actor, *, leave_type: str, duration: Decimal, justification: str, idempotency_key: str
) -> HRRequest:
    record = _employee_record(actor, "hreis.leave.create")
    key = _key(idempotency_key)
    policy = current_policy("leave")
    valid = _validated_leave(actor, policy, leave_type, duration, justification)
    route = _route("leave", actor.kind, record.department, policy)
    move = workflow.resolve(
        "leave",
        "draft",
        "submit",
        "employee",
        guard_results={
            "supported_leave_type": True,
            "required_fields": True,
            "balance_valid": True,
            "eligibility_valid": True,
            "route_configured": True,
        },
    )
    return _persist(
        actor,
        family="leave",
        subtype=leave_type,
        state=move.target,
        payload={"duration": str(valid.duration), "justification": valid.justification},
        policy=policy,
        transition=move,
        key=key,
        route=route,
    )


@transaction.atomic
def submit_claim(
    actor,
    *,
    family: str,
    subtype: str,
    prescribed_form_reference: str = "",
    purpose: str = "",
    amount: Decimal | None = None,
    document_references=(),
    idempotency_key: str,
) -> HRRequest:
    _employee_record(actor, "hreis.claim.create")
    key = _key(idempotency_key)
    if family not in {"ltc", "cpda"}:
        raise BadRequestError("Choose LTC or CPDA.", code="invalid_claim_family")
    policy = current_policy(family)
    if family == "ltc":
        try:
            valid = claims.validate_ltc(subtype, prescribed_form_reference)
        except claims.InvalidClaim as exc:
            raise BadRequestError(str(exc), code=exc.code) from exc
        detail = {"prescribed_form_reference": valid.prescribed_form_reference}
        payload = {"prescribed_form_reference": valid.prescribed_form_reference}
        guards = {"prescribed_form_present": True}
    else:
        try:
            valid = claims.validate_cpda(subtype, purpose, amount, document_references)
        except claims.InvalidClaim as exc:
            raise BadRequestError(str(exc), code=exc.code) from exc
        detail = {"purpose": valid.purpose, "amount": valid.amount}
        # A submitted reference does not prove a trusted upload or verification.
        payload = {"document_references": list(valid.document_references)}
        guards = {"purpose_present": True, "amount_present": True, "documents_present": True}
    move = workflow.resolve(family, "draft", "submit", "employee", guard_results=guards)
    row = _persist(
        actor,
        family=family,
        subtype=subtype,
        state=move.target,
        payload=payload,
        policy=policy,
        transition=move,
        key=key,
    )
    ClaimDetail.objects.create(request=row, claim_type=family, subtype=subtype, **detail)
    return row


def _require_open_appraisal_window(policy):
    window = policy.parameters.get("submission_window")
    if not isinstance(window, dict):
        raise ConflictError(
            "Appraisal submission dates are not configured. Contact HR to resolve this before "
            "retrying.",
            code="appraisal_window_missing",
        )
    start = datetime.fromisoformat(window["start"])
    end = datetime.fromisoformat(window["end"])
    now = timezone.now()
    if not start <= now < end:
        raise ConflictError(
            "The appraisal submission window is closed. Contact HR to resolve this before "
            "retrying.",
            code="appraisal_window_closed",
        )


def _create_appraisal_detail(row, record, period_key, submitted_form):
    try:
        with transaction.atomic():
            AppraisalDetail.objects.create(
                request=row,
                employee_record=record,
                period_key=period_key,
                submitted_form=submitted_form,
            )
    except IntegrityError as exc:
        constraint = getattr(getattr(exc.__cause__, "diag", None), "constraint_name", None)
        if constraint != "hr_appraisal_record_period_unique":
            raise
        raise ConflictError(
            "An appraisal already exists for this period. Open it in Annual Appraisals.",
            code="appraisal_already_submitted",
        ) from exc


@transaction.atomic
def submit_appraisal(
    actor, *, period_key: str, submitted_form: dict, idempotency_key: str
) -> HRRequest:
    record = _employee_record(actor, "hreis.appraisal.create")
    key = _key(idempotency_key)
    if not isinstance(period_key, str) or not period_key.strip() or len(period_key) > 80:
        raise BadRequestError("Provide the appraisal period.", code="invalid_period")
    if not isinstance(submitted_form, dict) or not submitted_form:
        raise BadRequestError(
            "Provide the completed appraisal form.", code="missing_appraisal_form"
        )
    period_key = period_key.strip()
    # The owner row serializes the duplicate check even before an appraisal exists.
    EmployeeServiceRecord.objects.select_for_update().get(pk=record.pk)
    policy = current_policy("appraisal")
    _require_open_appraisal_window(policy)
    if HRRequest.objects.filter(
        family="appraisal",
        user_id=actor.user_id,
        appraisal__period_key=period_key,
    ).exists():
        raise ConflictError(
            "This period already has an appraisal. Contact HR to resolve this before retrying.",
            code="appraisal_already_submitted",
        )
    move = workflow.resolve(
        "appraisal",
        "not_submitted",
        "submit",
        "employee",
        guard_results={"submission_window_open": True},
    )
    row = _persist(
        actor,
        family="appraisal",
        subtype="",
        state=move.target,
        payload={"period_key": period_key},
        policy=policy,
        transition=move,
        key=key,
    )
    _create_appraisal_detail(row, record, period_key, submitted_form)
    return row
