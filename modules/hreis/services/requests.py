"""Employee HR request submission, validated against active institutional policy.

This module does not invent leave quotas, approval authorities, appraisal windows,
document verification outcomes, or financial approval. Each record is an atomic
request, transition, audit event and dashboard notification.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from django.db import transaction
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
            "Your official service record is not yet available.", code="employee_record_missing"
        )
    return row


def _key(key: str) -> str:
    if not isinstance(key, str) or not 1 <= len(key) <= 100 or not key.strip():
        raise BadRequestError("Provide a unique operation key.", code="missing_idempotency_key")
    if HRRequestTransition.objects.filter(idempotency_key=key).exists():
        raise ConflictError("This request has already been submitted.", code="operation_replayed")
    return key


def _route(family: str, kind: str, department: str, policy) -> routing.ApprovalRoute:
    route_rows = policy.parameters.get("routes")
    if not isinstance(route_rows, list):
        raise ConflictError(
            "No approval routes are configured for this policy.", code="policy_route_missing"
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
        for index, designation in enumerate(route.authorities):
            ApprovalRouteStep.objects.create(
                request=row,
                position=index,
                designation=designation,
                policy_version_label=route.version,
            )
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
    return row


@transaction.atomic
def submit_leave(
    actor, *, leave_type: str, duration: Decimal, justification: str, idempotency_key: str
) -> HRRequest:
    record = _employee_record(actor, "hreis.leave.create")
    key = _key(idempotency_key)
    policy = current_policy("leave")
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
        # Document references are unverified at submission; no ClaimDocument
        # records are invented until a trusted upload service can validate them.
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


@transaction.atomic
def submit_appraisal(
    actor, *, period_key: str, submitted_form: dict, idempotency_key: str
) -> HRRequest:
    _employee_record(actor, "hreis.appraisal.create")
    key = _key(idempotency_key)
    if not isinstance(period_key, str) or not period_key.strip() or len(period_key) > 80:
        raise BadRequestError("Provide the appraisal period.", code="invalid_period")
    if not isinstance(submitted_form, dict) or not submitted_form:
        raise BadRequestError(
            "Provide the completed appraisal form.", code="missing_appraisal_form"
        )
    policy = current_policy("appraisal")
    window = policy.parameters.get("submission_window")
    if not isinstance(window, dict):
        raise ConflictError(
            "Appraisal submission dates are not configured.", code="appraisal_window_missing"
        )
    start = datetime.fromisoformat(window["start"])
    end = datetime.fromisoformat(window["end"])
    now = timezone.now()
    if not start <= now < end:
        raise ConflictError(
            "The appraisal submission window is closed.", code="appraisal_window_closed"
        )
    if HRRequest.objects.filter(
        family="appraisal",
        user_id=actor.user_id,
        appraisal__period_key=period_key,
    ).exists():
        raise ConflictError(
            "This period already has an appraisal.", code="appraisal_already_submitted"
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
    AppraisalDetail.objects.create(
        request=row,
        period_key=period_key,
        submitted_form=submitted_form,
    )
    return row
