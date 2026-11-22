from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal, InvalidOperation

from django.db import IntegrityError, transaction
from django.db.models import Q, Sum
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.directory.contracts import get_users
from modules.hreis.domain import state_machine as sm
from modules.hreis.models import (
    AuditEvent,
    EmployeeServiceRecord,
    HRPolicyVersion,
    HRRequest,
    LeaveBalanceEntry,
    NotificationRecord,
    RequestDecision,
)

SUPPORTED_LEAVE_TYPES = frozenset(
    {
        "casual",
        "restricted",
        "medical",
        "earned",
        "vacation",
        "sabbatical",
    }
)
SUPPORTED_APPROVAL_ROLES = frozenset(
    {
        "hradmin",
        "SectionHead_HR",
        "Accounts Admin",
        "Director",
        "Registrar",
        "HOD (CSE)",
        "HOD (ECE)",
        "HOD (ME)",
        "HOD (Design)",
        "HOD (NS)",
        "HOD (Liberal Arts)",
    }
)


def _fail(message, code):
    raise BadRequestError(message, code=code)


def _fingerprint(value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _required_idempotency_key(key):
    if not isinstance(key, str) or not 8 <= len(key) <= 100:
        _fail(
            "Provide an Idempotency-Key between 8 and 100 characters.", "idempotency_key_required"
        )
    return key


def _active_policy(name="hr"):
    today = timezone.localdate()
    policy = (
        HRPolicyVersion.objects.filter(
            policy_name=name,
            effective_from__lte=today,
        )
        .filter(
            effective_to__isnull=True,
        )
        .order_by("-version")
        .first()
    )
    if policy is None:
        policy = (
            HRPolicyVersion.objects.filter(
                policy_name=name,
                effective_from__lte=today,
                effective_to__gte=today,
            )
            .order_by("-version")
            .first()
        )
    if policy is None:
        _fail(
            (
                "HR policy is not configured for today. Ask an HR administrator to "
                "publish an effective policy version."
            ),
            "hr_policy_missing",
        )
    return policy


def _employee_record(user_id):
    try:
        return EmployeeServiceRecord.objects.get(user_id=user_id)
    except EmployeeServiceRecord.DoesNotExist as exc:
        raise BadRequestError(
            (
                "Your HR service record is missing an employee category. Ask HR to "
                "complete it before submitting this request."
            ),
            code="employee_record_missing",
        ) from exc


def _configured_route(payload, request_type, category):
    routes = payload.get("approval_routes", {})
    route = routes.get(request_type, {}).get(category)
    if (
        not isinstance(route, list)
        or not route
        or not all(isinstance(role, str) and role.strip() for role in route)
    ):
        _fail(
            (
                f"No approval route is configured for {request_type} and employee "
                f"category {category}. Ask an HR administrator to configure it."
            ),
            "approval_route_missing",
        )
    if any(role not in SUPPORTED_APPROVAL_ROLES for role in route):
        _fail(
            "The approval route contains a designation not present in the approved HR role list.",
            "unknown_approval_designation",
        )
    return route


def _balance(user_id, leave_type):
    value = LeaveBalanceEntry.objects.filter(
        user_id=user_id,
        leave_type=leave_type,
    ).aggregate(total=Sum("delta_days"))["total"]
    return value or Decimal("0")


def _validate_request(request_type, data, category, payload, user_id):
    if not isinstance(data, dict):
        _fail("Request data must be an object.", "invalid_request_data")
    cycle_key = ""
    if request_type == "leave":
        leave_type = data.get("leave_type")
        if leave_type not in SUPPORTED_LEAVE_TYPES:
            _fail("Choose one of the supported leave types.", "unsupported_leave_type")
        try:
            days = Decimal(str(data.get("duration_days", "")))
        except (InvalidOperation, ValueError):
            _fail("Enter a valid leave duration in days.", "invalid_leave_duration")
        if (
            not days.is_finite()
            or days <= 0
            or not isinstance(data.get("justification"), str)
            or not data["justification"].strip()
        ):
            _fail("Enter a positive leave duration and a justification.", "leave_fields_required")
        eligible = payload.get("eligible_leave_types", {}).get(category)
        if not isinstance(eligible, list):
            _fail(
                (
                    "Leave eligibility is not configured for your employee category. Ask HR "
                    "to configure policy."
                ),
                "leave_policy_missing",
            )
        if leave_type not in eligible:
            _fail(
                "Your current HR policy does not allow this leave type for your employee category.",
                "leave_not_eligible",
            )
        if _balance(user_id, leave_type) < days:
            _fail(
                "Your recorded leave balance is insufficient. Contact HR to verify your balance.",
                "insufficient_leave_balance",
            )
    elif request_type == "appraisal":
        cycle_key = str(data.get("cycle_key", "")).strip()
        windows = payload.get("appraisal_windows", {})
        window = windows.get(cycle_key)
        if not cycle_key or not isinstance(window, dict):
            _fail(
                "No appraisal window is configured for this cycle. Ask HR to configure it.",
                "appraisal_window_missing",
            )
        today = timezone.localdate()
        try:
            opens = date.fromisoformat(window["opens"])
            closes = date.fromisoformat(window["closes"])
        except (KeyError, TypeError, ValueError) as exc:
            raise BadRequestError(
                "The configured appraisal window is invalid. Ask HR to correct it.",
                code="invalid_appraisal_window",
            ) from exc
        if not opens <= today <= closes:
            _fail(
                "The appraisal submission window is closed. Contact HR for the current schedule.",
                "appraisal_window_closed",
            )
    elif request_type.startswith("ltc_"):
        if not isinstance(data.get("form_data"), dict) or not data["form_data"]:
            _fail("Complete the prescribed LTC form before submitting.", "ltc_form_required")
        if (
            not isinstance(data.get("supporting_documents"), list)
            or not data["supporting_documents"]
            or any(
                not isinstance(item, str) or not item.strip()
                for item in data["supporting_documents"]
            )
        ):
            _fail("Attach the documents required for LTC verification.", "ltc_documents_required")
    elif request_type.startswith("cpda_"):
        try:
            amount = Decimal(str(data.get("amount", "")))
        except (InvalidOperation, ValueError):
            _fail("Enter a valid CPDA amount.", "invalid_cpda_amount")
        if (
            not amount.is_finite()
            or amount <= 0
            or not isinstance(data.get("purpose"), str)
            or not data["purpose"].strip()
        ):
            _fail("Enter the CPDA purpose and a positive amount.", "cpda_fields_required")
        if (
            not isinstance(data.get("supporting_documents"), list)
            or not data["supporting_documents"]
            or any(
                not isinstance(item, str) or not item.strip()
                for item in data["supporting_documents"]
            )
        ):
            _fail("Attach the documents required for CPDA verification.", "cpda_documents_required")
    else:
        _fail("This HR request type is not supported.", "unsupported_request_type")
    return cycle_key


def _transition_facts(request, actor):
    current_role = actor.active_role or ""
    on_route = bool(request.approval_route) and (
        request.route_index < len(request.approval_route)
        and request.approval_route[request.route_index] == current_role
    )
    next_exists = request.route_index + 1 < len(request.approval_route)
    return {
        "current_actor_is_authority": on_route,
        "is_not_request_owner": actor.user_id != request.owner_user_id,
        "route_exists": bool(request.approval_route),
        "final_authority": on_route and not next_exists,
        "configured_next_authority_exists": on_route and next_exists,
        "accountant_processing_details_valid": True,
        "hr_verification_complete": True,
        "reviewers_assigned": True,
    }


def _write_event(request, actor, action, details=None):
    AuditEvent.objects.create(
        user_id=request.owner_user_id,
        actor_user_id=actor.user_id,
        actor_role=actor.active_role or "",
        action=action,
        resource_type="hr_request",
        resource_id=request.pk,
        details=details or {},
    )
    NotificationRecord.objects.create(
        user_id=request.owner_user_id,
        topic=f"request.{action}",
        request=request,
        payload={"request_type": request.request_type, "state": request.state},
    )


@transaction.atomic
def create_request(*, actor, request_type, data, idempotency_key):
    if not actor.has_permission("hreis.request.create"):
        raise PermissionDeniedError("Your active role cannot submit HR requests.")
    idempotency_key = _required_idempotency_key(idempotency_key)
    fingerprint = _fingerprint({"request_type": request_type, "data": data})
    replay = HRRequest.objects.filter(
        owner_user_id=actor.user_id, submission_key=idempotency_key
    ).first()
    if replay is not None:
        if replay.submission_fingerprint != fingerprint:
            raise ConflictError(
                "This Idempotency-Key was already used for different request data.",
                code="idempotency_key_reused",
            )
        return replay
    if request_type not in {value for value, _ in HRRequest.REQUEST_TYPES}:
        _fail("Choose a supported HR request type.", "unsupported_request_type")
    record = _employee_record(actor.user_id)
    policy = _active_policy()
    cycle_key = _validate_request(
        request_type, data, record.employee_category, policy.payload, actor.user_id
    )
    route = _configured_route(policy.payload, request_type, record.employee_category)
    if request_type == "appraisal":
        route = _configured_route(policy.payload, "appraisal", record.employee_category)
    try:
        with transaction.atomic():
            request = HRRequest.objects.create(
                owner_user_id=actor.user_id,
                submission_key=idempotency_key,
                submission_fingerprint=fingerprint,
                request_type=request_type,
                cycle_key=cycle_key,
                data=data,
                approval_route=route,
                current_authority_designation=route[0],
                policy_version_id=policy.pk,
            )
    except IntegrityError as exc:
        replay = HRRequest.objects.filter(
            owner_user_id=actor.user_id, submission_key=idempotency_key
        ).first()
        if replay is not None and replay.submission_fingerprint == fingerprint:
            return replay
        if replay is not None:
            raise ConflictError(
                "This Idempotency-Key was already used for different request data.",
                code="idempotency_key_reused",
            ) from exc
        if (
            request_type == "appraisal"
            and HRRequest.objects.filter(
                owner_user_id=actor.user_id,
                request_type=request_type,
                cycle_key=cycle_key,
            ).exists()
        ):
            raise ConflictError(
                "An appraisal request already exists for this cycle.",
                code="appraisal_cycle_exists",
            ) from exc
        raise
    facts = {
        "valid_required_fields": True,
        "supported_leave_type": True,
        "balance_and_eligibility": True,
        "route_exists": bool(route),
        "window_open": True,
        "prescribed_form": bool(data.get("form_data")),
        "documentation_and_eligibility": bool(data.get("supporting_documents")),
        "purpose_and_amount": bool(data.get("purpose") and data.get("amount")),
        "supporting_documents": bool(data.get("supporting_documents")),
    }
    resource = (
        "leave"
        if request_type == "leave"
        else (
            "appraisal"
            if request_type == "appraisal"
            else "ltc"
            if request_type.startswith("ltc_")
            else "cpda"
        )
    )
    actor_kind = sm.EMPLOYEE
    target = sm.apply(resource, sm.DRAFT, "submit", actor_kind, facts)
    request.state = target
    request.save(update_fields=["state", "updated_at"])
    RequestDecision.objects.create(
        request=request,
        from_state=sm.DRAFT,
        event="submit",
        to_state=request.state,
        actor_user_id=actor.user_id,
        actor_role=actor.active_role or "",
        idempotency_key=idempotency_key,
        details_fingerprint=_fingerprint({}),
    )
    _write_event(request, actor, "submitted")
    return request


@transaction.atomic
def transition_request(*, request_id, actor, event, note="", details=None, idempotency_key):
    idempotency_key = _required_idempotency_key(idempotency_key)
    details = details or {}
    try:
        request = HRRequest.objects.select_for_update().get(pk=request_id)
    except HRRequest.DoesNotExist as exc:
        raise NotFoundError("HR request was not found.", code="request_not_found") from exc
    previous = request.decisions.filter(idempotency_key=idempotency_key).first()
    details_fingerprint = _fingerprint(details)
    if previous is not None:
        if (
            previous.actor_user_id != actor.user_id
            or previous.event != event
            or previous.note != note[:500]
            or previous.details_fingerprint != details_fingerprint
        ):
            raise ConflictError(
                "This Idempotency-Key was already used for a different decision.",
                code="idempotency_key_reused",
            )
        return request
    old_state = request.state
    role = actor.active_role or ""
    resource = (
        "leave"
        if request.request_type == "leave"
        else "appraisal"
        if request.request_type == "appraisal"
        else "ltc"
        if request.request_type.startswith("ltc_")
        else "cpda"
    )
    actor_kind = {
        "assign_reviewers": sm.HR_ADMINISTRATOR,
        "verify": sm.HR_ADMINISTRATOR,
        "process": sm.ACCOUNTANT,
    }.get(event, sm.APPROVING_AUTHORITY)
    if event == "assign_reviewers":
        if not actor.has_permission("hreis.request.assign"):
            raise PermissionDeniedError("Your active role cannot assign appraisal reviewers.")
    elif event == "verify":
        if not actor.has_permission("hreis.request.manage"):
            raise PermissionDeniedError("Your active role cannot perform this HR verification.")
    elif event == "process":
        if not actor.has_permission("hreis.claim.update"):
            raise PermissionDeniedError("Your active role cannot process approved claims.")
    elif not actor.has_permission("hreis.request.review"):
        raise PermissionDeniedError("Your active role cannot decide this HR request.")
    facts = _transition_facts(request, actor)
    if event == "assign_reviewers":
        reviewers = details.get("reviewer_user_ids")
        if (
            not isinstance(reviewers, list)
            or not reviewers
            or not all(type(uid) is int and uid > 0 for uid in reviewers)
            or len(reviewers) != len(set(reviewers))
            or request.owner_user_id in reviewers
        ):
            _fail(
                "Assign at least one valid reviewer before continuing.",
                "reviewer_assignment_required",
            )
        reviewer_refs = get_users(reviewers)
        if set(reviewer_refs) != set(reviewers) or any(
            reviewer_refs[uid].kind not in {"faculty", "staff"} for uid in reviewers
        ):
            _fail(
                "Appraisal reviewers must be existing faculty or staff members.",
                "invalid_appraisal_reviewer",
            )
        request.data = {**request.data, "reviewer_user_ids": reviewers}
        facts["reviewers_assigned"] = True
    if event == "process":
        financial_status = details.get("financial_status")
        if not isinstance(financial_status, str) or not financial_status.strip():
            _fail(
                "Record the received financial status before completing processing.",
                "financial_status_required",
            )
        request.data = {**request.data, "financial_processing": details}
        facts["accountant_processing_details_valid"] = True
    target = sm.apply(resource, old_state, event, actor_kind, facts)
    if event == "forward":
        request.route_index += 1
    request.state = target
    request.current_authority_designation = (
        request.approval_route[request.route_index]
        if request.route_index < len(request.approval_route)
        else ""
    )
    request.save(
        update_fields=[
            "state",
            "route_index",
            "current_authority_designation",
            "data",
            "updated_at",
        ]
    )
    if event == "approve" and resource == "leave":
        EmployeeServiceRecord.objects.select_for_update().get(user_id=request.owner_user_id)
        days = Decimal(str(request.data["duration_days"]))
        if _balance(request.owner_user_id, request.data["leave_type"]) < days:
            _fail(
                "The recorded leave balance changed and is now insufficient. Ask HR to review it.",
                "insufficient_leave_balance",
            )
        LeaveBalanceEntry.objects.create(
            user_id=request.owner_user_id,
            leave_type=request.data["leave_type"],
            delta_days=-days,
            request=request,
            reason="Approved leave request",
            actor_user_id=actor.user_id,
        )
    RequestDecision.objects.create(
        request=request,
        from_state=old_state,
        event=event,
        to_state=target,
        actor_user_id=actor.user_id,
        actor_role=role,
        note=note[:500],
        idempotency_key=idempotency_key,
        details_fingerprint=details_fingerprint,
    )
    _write_event(request, actor, event, details)
    return request


@transaction.atomic
def maintain_employee_record(*, actor, user_id, values):
    if not actor.has_permission("hreis.employee.manage"):
        raise PermissionDeniedError(
            "Only an authorized HR administrator may maintain service records."
        )
    allowed = {
        "employee_category",
        "appointment_details",
        "department_code",
        "designation",
        "service_history",
        "retirement_status",
    }
    if set(values) - allowed:
        _fail(
            "The service record contains fields that cannot be changed.",
            "invalid_service_record_fields",
        )
    if not values:
        _fail("Provide at least one service-record field to update.", "empty_service_record_update")
    record = EmployeeServiceRecord.objects.select_for_update().filter(user_id=user_id).first()
    if record is None:
        category = values.get("employee_category")
        if not category:
            _fail(
                "Set the employee category when creating a service record.",
                "employee_category_required",
            )
        record = EmployeeServiceRecord(user_id=user_id, employee_category=category)
    for key, value in values.items():
        setattr(record, key, value)
    record.updated_by_user_id = actor.user_id
    record.save()
    AuditEvent.objects.create(
        user_id=user_id,
        actor_user_id=actor.user_id,
        actor_role=actor.active_role or "",
        action="employee_record_updated",
        resource_type="employee_service_record",
        resource_id=record.pk,
    )
    return record


@transaction.atomic
def create_policy_version(*, actor, policy_name, version, effective_from, effective_to, payload):
    if not actor.has_permission("hreis.policy.manage"):
        raise PermissionDeniedError("Only an authorized HR administrator may publish HR policy.")
    if not isinstance(payload, dict) or not payload:
        _fail("Provide the policy configuration as a non-empty object.", "policy_payload_required")
    if effective_to and effective_to < effective_from:
        _fail("The policy end date must not precede its start date.", "policy_dates_invalid")
    if HRPolicyVersion.objects.filter(policy_name=policy_name, version=version).exists():
        raise ConflictError("That policy version already exists.", code="policy_version_exists")
    overlap = HRPolicyVersion.objects.filter(
        policy_name=policy_name,
        effective_from__lte=effective_to or date.max,
    ).filter(Q(effective_to__isnull=True) | Q(effective_to__gte=effective_from))
    if effective_from < timezone.localdate():
        _fail("New policy versions cannot take effect retroactively.", "retroactive_policy_version")
    if overlap.exists():
        raise ConflictError(
            "Policy effective dates overlap an existing version. Choose a non-overlapping range.",
            code="policy_dates_overlap",
        )
    return HRPolicyVersion.objects.create(
        policy_name=policy_name,
        version=version,
        effective_from=effective_from,
        effective_to=effective_to,
        payload=payload,
    )


@transaction.atomic
def adjust_leave_balance(*, actor, user_id, leave_type, delta_days, reason):
    if not actor.has_permission("hreis.leave_balance.manage"):
        raise PermissionDeniedError("Your active role cannot adjust leave balances.")
    try:
        delta = Decimal(str(delta_days))
    except (InvalidOperation, ValueError) as exc:
        raise BadRequestError(
            "Enter a valid balance adjustment.", code="invalid_balance_adjustment"
        ) from exc
    if (
        not delta.is_finite()
        or delta == 0
        or not reason.strip()
        or leave_type not in SUPPORTED_LEAVE_TYPES
    ):
        _fail(
            "Choose a supported leave type, a non-zero adjustment, and a reason.",
            "invalid_balance_adjustment",
        )
    try:
        EmployeeServiceRecord.objects.select_for_update().get(user_id=user_id)
    except EmployeeServiceRecord.DoesNotExist as exc:
        raise BadRequestError(
            "Create the employee service record before adjusting leave balances.",
            code="employee_record_missing",
        ) from exc
    if _balance(user_id, leave_type) + delta < 0:
        _fail("A leave balance cannot be adjusted below zero.", "negative_leave_balance")
    entry = LeaveBalanceEntry.objects.create(
        user_id=user_id,
        leave_type=leave_type,
        delta_days=delta,
        reason=reason[:300],
        actor_user_id=actor.user_id,
    )
    AuditEvent.objects.create(
        user_id=user_id,
        actor_user_id=actor.user_id,
        actor_role=actor.active_role or "",
        action="leave_balance_adjusted",
        resource_type="leave_balance_entry",
        resource_id=entry.pk,
        details={"leave_type": leave_type, "delta_days": str(delta)},
    )
    return entry
