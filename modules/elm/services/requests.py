"""Transactional ELM write choke points. Views must not mutate ORM rows directly."""

from datetime import date
from decimal import Decimal

from django.db import connection, transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.elm.domain import workflow
from modules.elm.domain.counting import chargeable_days, intervals_overlap
from modules.elm.domain.errors import ElmDomainError
from modules.elm.models import (
    AuditEvent,
    CalendarVersion,
    LeaveLedgerEntry,
    LeavePolicy,
    LeaveRequest,
    WorkflowTask,
)

ENTITLEMENT_DEFAULTS = {"CL": 8, "RH": 2, "SCL": 15, "EL": 30, "COL": 20, "VL": 60}


def _has(actor, code):
    return bool(actor and getattr(actor, "has_permission", lambda _: False)(code))


def _effective(model, day):
    return (
        model.objects.filter(published_at__isnull=False, effective_from__lte=day)
        .filter(
            __import__("django.db").db.models.Q(effective_to__isnull=True)
            | __import__("django.db").db.models.Q(effective_to__gte=day)
        )
        .order_by("-effective_from", "-version")
        .first()
    )


def _calendar_closed_dates(calendar, start, end):
    closed = set()
    if calendar is None:
        return closed
    for value in calendar.holidays or []:
        try:
            closed.add(date.fromisoformat(value if isinstance(value, str) else value["date"]))
        except (ValueError, TypeError, KeyError):
            continue
    # Weekend treatment is applied only to the ordinary closed-day categories.
    current = start
    while current <= end:
        if current.weekday() >= 5:
            closed.add(current)
        current = date.fromordinal(current.toordinal() + 1)
    return closed


def _balance(user_id, category, day):
    # Positive credits and restores, negative debits/lapses. Policy crediting is
    # an explicit scheduled/admin operation, never silently synthesized here.
    rows = LeaveLedgerEntry.objects.filter(
        user_id=user_id, category=category, effective_date__lte=day
    )
    total = Decimal("0")
    for row in rows.only("amount", "entry_type"):
        if row.entry_type in {"credit", "restore", "conversion", "adjustment"}:
            total += row.amount
        elif row.entry_type in {"debit", "lapse"}:
            total -= row.amount
    return total


def _audit(req, actor, event, old="", new="", reason="", payload=None):
    AuditEvent.objects.create(
        request=req,
        actor_user_id=getattr(actor, "user_id", None),
        event_type=event,
        from_status=old,
        to_status=new,
        reason=reason,
        payload=payload or {},
    )


def _validate(
    actor,
    *,
    category,
    start,
    end,
    half_day,
    purpose,
    substitute_user_id,
    station_leave,
    station_leave_details,
    medical_evidence_ref,
    exclude_id=None,
):
    # Serialize concurrent submissions for one employee on PostgreSQL. Without
    # this lock two first-time requests could both pass overlap/balance checks.
    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_xact_lock(%s, %s)", [78104, int(actor.user_id)])
    if category not in ENTITLEMENT_DEFAULTS:
        raise ConflictError("Unsupported leave category.", code="invalid_category")
    if station_leave and not station_leave_details:
        raise ConflictError(
            "Station Leave details are required when Station Leave applies.",
            code="station_leave_details_required",
        )
    if end < start:
        raise ConflictError("End date cannot precede start date.", code="invalid_period")
    if not purpose.strip():
        raise ConflictError("A purpose/reason is required.", code="purpose_required")
    policy = _effective(LeavePolicy, start)
    calendar = _effective(CalendarVersion, start)
    if policy is None:
        raise ConflictError(
            "No published leave policy is effective for this date.", code="policy_unavailable"
        )
    if calendar is None:
        raise ConflictError(
            "No published holiday/RH calendar is effective for this date.",
            code="calendar_unavailable",
        )
    params = policy.parameters or {}
    allowed = params.get("eligible_categories_by_kind", {}).get(getattr(actor, "kind", ""))
    if not isinstance(allowed, list) or category not in allowed:
        raise ConflictError(
            (
                "Eligibility is not configured for this employee kind/category "
                "in the effective policy."
            ),
            code="not_eligible",
        )
    if category == "RH":
        rh = set(calendar.restricted_holidays or [])
        dates = {start.isoformat()} if start == end else set()
        if not dates.intersection(rh):
            raise ConflictError(
                "RH must match a published Restricted Holiday date.", code="rh_date_invalid"
            )
    if category == "VL":
        in_vacation = any(
            (item.get("start") <= start.isoformat() and item.get("end") >= end.isoformat())
            for item in (calendar.vacation_periods or [])
            if isinstance(item, dict) and item.get("start") and item.get("end")
        )
        if not in_vacation:
            raise ConflictError(
                "VL is permitted only inside a published vacation period.",
                code="vacation_period_required",
            )
    if (
        category == "COL"
        and params.get("col_requires_medical_evidence", False)
        and not medical_evidence_ref
    ):
        raise ConflictError(
            "Supporting medical evidence is required by the effective policy.",
            code="medical_evidence_required",
        )
    if substitute_user_id is not None:
        if substitute_user_id == actor.user_id:
            raise ConflictError(
                "An employee cannot nominate themselves as substitute.", code="invalid_substitute"
            )
        if substitute_user_id <= 0:
            raise ConflictError("Substitute user id is invalid.", code="invalid_substitute")
        if LeaveRequest.objects.filter(
            user_id=substitute_user_id,
            status__in=[
                workflow.AWAITING_SUBSTITUTE,
                workflow.UNIT_HEAD_REVIEW,
                workflow.ESTABLISHMENT_REVIEW,
                workflow.AUTHORITY_REVIEW,
                workflow.APPROVED,
            ],
            start_date__lte=end,
            end_date__gte=start,
        ).exists():
            raise ConflictError(
                "The nominated substitute has overlapping leave.", code="substitute_overlap"
            )
    closed = _calendar_closed_dates(calendar, start, end)
    try:
        days = chargeable_days(category, start, end, closed_dates=closed, half_day=half_day)
    except ElmDomainError as exc:
        raise ConflictError(str(exc), code=exc.code) from exc
    for req in LeaveRequest.objects.filter(
        user_id=actor.user_id,
        status__in=[
            workflow.AWAITING_SUBSTITUTE,
            workflow.UNIT_HEAD_REVIEW,
            workflow.ESTABLISHMENT_REVIEW,
            workflow.AUTHORITY_REVIEW,
            workflow.APPROVED,
        ],
    ).exclude(pk=exclude_id):
        if intervals_overlap(start, end, req.start_date, req.end_date) and not (
            # Different halves of the same date are non-overlapping for CL.
            category == req.category == "CL"
            and start == end == req.start_date == req.end_date
            and half_day != "none"
            and req.half_day != "none"
            and half_day != req.half_day
        ):
            raise ConflictError(
                "The requested period overlaps another pending or approved leave."
            )
    balance = _balance(actor.user_id, category, start)
    if balance < days:
        raise ConflictError(
            f"Insufficient {category} balance: available {balance}, requested {days}.",
            code="insufficient_balance",
        )
    return days, policy, calendar


@transaction.atomic
def create_request(*, actor, data):
    if not _has(actor, "elm.request.create"):
        raise PermissionDeniedError("This action needs elm.request.create.")
    start = date.fromisoformat(str(data["start_date"]))
    end = date.fromisoformat(str(data["end_date"]))
    substitute = data.get("substitute_user_id")
    days, policy, calendar = _validate(
        actor,
        category=data["category"],
        start=start,
        end=end,
        half_day=data.get("half_day", "none"),
        purpose=data.get("purpose", ""),
        substitute_user_id=substitute,
        station_leave=data.get("station_leave", False),
        station_leave_details=data.get("station_leave_details", {}),
        medical_evidence_ref=data.get("medical_evidence_ref", ""),
    )
    director_self_sanction = getattr(actor, "active_role", None) == "Director"
    initial_status = (
        workflow.AWAITING_SUBSTITUTE
        if substitute
        else workflow.AUTHORITY_REVIEW
        if director_self_sanction
        else workflow.UNIT_HEAD_REVIEW
    )
    req = LeaveRequest.objects.create(
        user_id=actor.user_id,
        category=data["category"],
        start_date=start,
        end_date=end,
        half_day=data.get("half_day", "none"),
        chargeable_days=days,
        purpose=data["purpose"].strip(),
        station_leave=bool(data.get("station_leave", False)),
        station_leave_details=data.get("station_leave_details", {}),
        substitute_user_id=substitute,
        substitute_response="pending" if substitute else "",
        medical_evidence_ref=data.get("medical_evidence_ref", ""),
        policy_version_id=policy.pk,
        calendar_version_id=calendar.pk,
        status=initial_status,
        extra={"director_self_sanction": director_self_sanction},
        submitted_at=timezone.now(),
    )
    task_type = (
        "substitute_response"
        if substitute
        else "final_sanction"
        if director_self_sanction
        else "unit_head_review"
    )
    assigned_role = (
        "Substitute / Responsibility Holder"
        if substitute
        else "Director"
        if director_self_sanction
        else "Unit Head"
    )
    WorkflowTask.objects.create(
        request=req,
        task_type=task_type,
        assigned_user_id=substitute
        if substitute
        else actor.user_id
        if director_self_sanction
        else None,
        assigned_role=assigned_role,
    )
    _audit(
        req,
        actor,
        "request_submitted",
        "draft",
        req.status,
        payload={"policy_version_id": policy.pk, "calendar_version_id": calendar.pk},
    )
    return req


@transaction.atomic
def modify_request(*, actor, request_id, changes):
    req = (
        LeaveRequest.objects.select_for_update()
        .filter(pk=request_id, user_id=actor.user_id)
        .first()
    )
    if req is None:
        raise NotFoundError("Leave request not found.")
    if not _has(actor, "elm.request.modify"):
        raise PermissionDeniedError("This action needs elm.request.modify.")
    pending = {
        workflow.AWAITING_SUBSTITUTE,
        workflow.UNIT_HEAD_REVIEW,
        workflow.ESTABLISHMENT_REVIEW,
        workflow.AUTHORITY_REVIEW,
    }
    if req.status not in pending or req.kind != "leave":
        raise ConflictError(
            "Only a pending original leave request may be modified.",
            code="modification_not_allowed",
        )
    category = changes.get("category", req.category)
    start = changes.get("start_date", req.start_date)
    end = changes.get("end_date", req.end_date)
    half_day = changes.get("half_day", req.half_day)
    purpose = changes.get("purpose", req.purpose)
    substitute = changes.get("substitute_user_id", req.substitute_user_id)
    station_leave = changes.get("station_leave", req.station_leave)
    station_details = changes.get("station_leave_details", req.station_leave_details)
    medical_ref = changes.get("medical_evidence_ref", req.medical_evidence_ref)
    days, policy, calendar = _validate(
        actor,
        category=category,
        start=start,
        end=end,
        half_day=half_day,
        purpose=purpose,
        substitute_user_id=substitute,
        station_leave=station_leave,
        station_leave_details=station_details,
        medical_evidence_ref=medical_ref,
        exclude_id=req.pk,
    )
    old_status = req.status
    WorkflowTask.objects.filter(request=req, status="open").update(
        status="superseded", completed_at=timezone.now()
    )
    req.category = category
    req.start_date = start
    req.end_date = end
    req.half_day = half_day
    req.chargeable_days = days
    req.purpose = purpose.strip()
    req.substitute_user_id = substitute
    req.substitute_response = "pending" if substitute else ""
    req.station_leave = station_leave
    req.station_leave_details = station_details
    req.medical_evidence_ref = medical_ref
    req.policy_version_id = policy.pk
    req.calendar_version_id = calendar.pk
    req.status = workflow.AWAITING_SUBSTITUTE if substitute else workflow.UNIT_HEAD_REVIEW
    req.save()
    WorkflowTask.objects.create(
        request=req,
        task_type="substitute_response" if substitute else "unit_head_review",
        assigned_user_id=substitute,
        assigned_role="Substitute / Responsibility Holder" if substitute else "Unit Head",
    )
    _audit(
        req,
        actor,
        "request_modified",
        old_status,
        req.status,
        payload={"policy_version_id": policy.pk, "calendar_version_id": calendar.pk},
    )
    return req


@transaction.atomic
def respond_substitute(*, actor, request_id, accepted):
    req = (
        LeaveRequest.objects.select_for_update()
        .filter(pk=request_id, substitute_user_id=actor.user_id)
        .first()
    )
    if req is None:
        raise NotFoundError("Leave request not found.")
    if req.status != workflow.AWAITING_SUBSTITUTE or req.substitute_response != "pending":
        raise ConflictError("This substitute task is no longer pending.", code="task_not_pending")
    if not _has(actor, "elm.substitute.respond"):
        raise PermissionDeniedError("This action needs elm.substitute.respond.")
    old = req.status
    req.substitute_response = "accepted" if accepted else "declined"
    if accepted:
        director_self_sanction = bool((req.extra or {}).get("director_self_sanction"))
        req.status = (
            workflow.AUTHORITY_REVIEW if director_self_sanction else workflow.UNIT_HEAD_REVIEW
        )
        WorkflowTask.objects.filter(request=req, status="open").update(
            status="completed", completed_at=timezone.now()
        )
        WorkflowTask.objects.create(
            request=req,
            task_type="final_sanction" if director_self_sanction else "unit_head_review",
            assigned_user_id=req.user_id if director_self_sanction else None,
            assigned_role="Director" if director_self_sanction else "Unit Head",
        )
    else:
        # Decline does not route. Applicant must nominate another substitute or withdraw.
        req.extra = {**(req.extra or {}), "substitute_declined": True}
    req.save(update_fields=["substitute_response", "status", "extra", "updated_at"])
    _audit(
        req, actor, "substitute_accepted" if accepted else "substitute_declined", old, req.status
    )
    return req


@transaction.atomic
def transition_request(*, actor, request_id, target, reason="", recommendation=""):
    from modules.elm.selectors.requests import requests_for

    req = requests_for(actor).select_for_update().filter(pk=request_id).first()
    if req is None:
        raise NotFoundError("Leave request not found.")
    if target == workflow.WITHDRAWN and req.user_id != actor.user_id:
        raise PermissionDeniedError("Only the applicant may withdraw their request.")
    if target == workflow.WITHDRAWN and req.status not in {
        workflow.DRAFT,
        workflow.AWAITING_SUBSTITUTE,
        workflow.UNIT_HEAD_REVIEW,
        workflow.ESTABLISHMENT_REVIEW,
        workflow.AUTHORITY_REVIEW,
    }:
        raise ConflictError(
            "Only a pending request can be withdrawn.", code="withdrawal_not_allowed"
        )
    if (
        target == workflow.CANCELLATION_PENDING
        and (
            req.status != workflow.APPROVED
            or req.start_date <= timezone.localdate()
        )
    ):
        raise ConflictError(
            "Approved leave can be cancelled only before its start date.",
            code="cancellation_not_allowed",
        )

    if req.status == workflow.UNIT_HEAD_REVIEW:
        if req.category in {"SCL", "EL", "COL", "VL"}:
            if target in {workflow.APPROVED, workflow.REJECTED}:
                raise ConflictError(
                    "Unit Head recommendation is not the final "
                    "sanctioning decision for this category.",
                    code="higher_sanction_required",
                )
            if target == workflow.ESTABLISHMENT_REVIEW and recommendation not in {
                "recommended",
                "not_recommended",
            }:
                raise ConflictError(
                    "Record Recommended or Not Recommended before routing higher-sanction leave.",
                    code="recommendation_required",
                )
        elif req.category in {"CL", "RH"} and target == workflow.ESTABLISHMENT_REVIEW:
            raise ConflictError(
                "CL/RH final decision belongs to the Unit Head in the study baseline.",
                code="unit_head_final_scope",
            )
    if (
        req.user_id == actor.user_id
        and target in {workflow.APPROVED, workflow.REJECTED}
        and not (
            (req.extra or {}).get("director_self_sanction")
            and getattr(actor, "active_role", None) == "Director"
            and target == workflow.APPROVED
        )
    ):
        raise PermissionDeniedError(
            "Self-sanction is permitted only for the configured Director-specific path."
        )
    actor_lane = None
    if req.user_id == actor.user_id and target == workflow.WITHDRAWN:
        actor_lane = "employee"
    elif req.status == workflow.UNIT_HEAD_REVIEW and _has(actor, "elm.request.review"):
        actor_lane = "unit_head"
    elif req.status == workflow.ESTABLISHMENT_REVIEW and _has(actor, "elm.request.route"):
        actor_lane = "establishment"
    elif req.status in {workflow.AUTHORITY_REVIEW, workflow.CANCELLATION_PENDING} and _has(
        actor, "elm.request.sanction"
    ):
        actor_lane = "authority"
    elif req.status == workflow.RESUMPTION_PENDING and _has(actor, "elm.request.verify_resume"):
        actor_lane = "unit_head"
    if target in {
        workflow.CANCELLATION_PENDING,
        workflow.EXTENSION_PENDING,
        workflow.RESUMPTION_PENDING,
    }:
        raise ConflictError(
            "Cancellation, extension and resumption must be separate linked requests.",
            code="related_request_required",
        )
    if actor_lane is None:
        raise PermissionDeniedError("Your permissions do not allow this transition.")
    try:
        trans = workflow.resolve(req.status, target, actor_lane)
    except ElmDomainError as exc:
        raise ConflictError(str(exc), code=exc.code) from exc
    if not _has(actor, trans.permission):
        raise PermissionDeniedError(f"This action needs {trans.permission}.")
    old = req.status
    if target == workflow.ESTABLISHMENT_REVIEW and req.category in {"SCL", "EL", "COL", "VL"}:
        req.extra = {
            **(req.extra or {}),
            "unit_head_recommendation": recommendation,
            "unit_head_recommendation_reason": reason.strip(),
        }
    req.status = target
    req.decision_reason = reason.strip()
    if target in {workflow.APPROVED, workflow.REJECTED, workflow.CANCELLED, workflow.CLOSED}:
        req.decided_at = timezone.now()
    req.save(update_fields=["status", "decision_reason", "decided_at", "updated_at"])
    WorkflowTask.objects.filter(request=req, status="open").update(
        status="completed", completed_at=timezone.now()
    )
    if target == workflow.ESTABLISHMENT_REVIEW:
        WorkflowTask.objects.create(
            request=req, task_type="establishment_review", assigned_role="Deputy Registrar (Estt.)"
        )
    elif target == workflow.AUTHORITY_REVIEW:
        resolved_role = (req.extra or {}).get("resolved_authority_role")
        WorkflowTask.objects.create(
            request=req,
            task_type="final_sanction",
            assigned_role=resolved_role or "UNCONFIGURED_AUTHORITY",
        )
    elif target == workflow.CANCELLATION_PENDING:
        WorkflowTask.objects.create(
            request=req, task_type="cancellation_review", assigned_role="UNCONFIGURED_AUTHORITY"
        )
    elif target == workflow.RESUMPTION_PENDING:
        WorkflowTask.objects.create(
            request=req, task_type="resumption_verification", assigned_role="Unit Head"
        )
    if target in {workflow.APPROVED, workflow.CANCELLED, workflow.CLOSED}:
        if target == workflow.APPROVED and req.kind in {"leave", "extension"}:
            key = f"leave:{req.pk}:debit"
            LeaveLedgerEntry.objects.get_or_create(
                idempotency_key=key,
                defaults={
                    "user_id": req.user_id,
                    "category": req.category,
                    "amount": req.chargeable_days,
                    "entry_type": "debit",
                    "effective_date": req.start_date,
                    "request": req,
                    "actor_user_id": actor.user_id,
                    "note": "Approved leave debit",
                },
            )
        if target == workflow.CANCELLED:
            parent = req.parent_request or req
            key = f"leave:{parent.pk}:restore"
            LeaveLedgerEntry.objects.get_or_create(
                idempotency_key=key,
                defaults={
                    "user_id": parent.user_id,
                    "category": parent.category,
                    "amount": parent.chargeable_days,
                    "entry_type": "restore",
                    "effective_date": timezone.localdate(),
                    "request": parent,
                    "actor_user_id": actor.user_id,
                    "note": "Approved leave cancellation restore",
                },
            )
            if req.parent_request_id:
                parent.status = workflow.CANCELLED
                parent.decided_at = timezone.now()
                parent.save(update_fields=["status", "decided_at", "updated_at"])
        if target == workflow.CLOSED and req.kind == "resumption" and req.parent_request_id:
            parent = req.parent_request
            if req.actual_resumption_date and req.actual_resumption_date < parent.end_date:
                from modules.elm.domain.counting import chargeable_days

                restore_start = date.fromordinal(req.actual_resumption_date.toordinal() + 1)
                closed = _calendar_closed_dates(
                    _effective(CalendarVersion, restore_start), restore_start, parent.end_date
                )
                unused = chargeable_days(
                    parent.category, restore_start, parent.end_date, closed_dates=closed
                )
                if unused > 0:
                    key = f"leave:{parent.pk}:early-return:{req.actual_resumption_date.isoformat()}"
                    LeaveLedgerEntry.objects.get_or_create(
                        idempotency_key=key,
                        defaults={
                            "user_id": parent.user_id,
                            "category": parent.category,
                            "amount": unused,
                            "entry_type": "restore",
                            "effective_date": req.actual_resumption_date,
                            "request": parent,
                            "actor_user_id": actor.user_id,
                            "note": "Unused leave restored after verified early resumption",
                        },
                    )
            parent.status = workflow.CLOSED
            parent.decided_at = timezone.now()
            parent.save(update_fields=["status", "decided_at", "updated_at"])
    _audit(req, actor, "status_transition", old, target, reason)
    return req


@transaction.atomic
def create_related_request(*, actor, parent_id, kind, data):
    """Create cancellation/extension/resumption as separate linked records."""
    parent = (
        LeaveRequest.objects.select_for_update().filter(pk=parent_id, user_id=actor.user_id).first()
    )
    if parent is None:
        raise NotFoundError("Leave request not found.")
    if parent.status != workflow.APPROVED:
        raise ConflictError(
            "A related request requires an approved parent leave.", code="parent_not_approved"
        )
    today = timezone.localdate()
    if kind == "cancellation":
        if parent.start_date <= today:
            raise ConflictError(
                "Approved leave can be cancelled only before it begins.",
                code="cancellation_not_allowed",
            )
        if not _has(actor, "elm.request.cancel"):
            raise PermissionDeniedError("This action needs elm.request.cancel.")
        related = LeaveRequest.objects.create(
            user_id=actor.user_id,
            category=parent.category,
            kind="cancellation",
            status=workflow.CANCELLATION_PENDING,
            start_date=parent.start_date,
            end_date=parent.end_date,
            chargeable_days=parent.chargeable_days,
            purpose=data.get("purpose", "Cancellation of approved leave"),
            parent_request=parent,
            policy_version_id=parent.policy_version_id,
            calendar_version_id=parent.calendar_version_id,
            submitted_at=timezone.now(),
        )
        WorkflowTask.objects.create(
            request=related, task_type="cancellation_review", assigned_role="UNCONFIGURED_AUTHORITY"
        )
    elif kind == "extension":
        if parent.category not in {"EL", "COL", "VL"} or not (
            parent.start_date <= today <= parent.end_date
        ):
            raise ConflictError(
                "Only ongoing EL, COL or VL can be extended.", code="extension_not_allowed"
            )
        if not _has(actor, "elm.request.extend"):
            raise PermissionDeniedError("This action needs elm.request.extend.")
        start = date.fromisoformat(str(data["start_date"]))
        end = date.fromisoformat(str(data["end_date"]))
        if start <= parent.end_date:
            raise ConflictError(
                "Extension period must begin after the approved period.",
                code="extension_period_invalid",
            )
        substitute = data.get("substitute_user_id")
        days, policy, calendar = _validate(
            actor,
            category=parent.category,
            start=start,
            end=end,
            half_day="none",
            purpose=data.get("purpose", "Extension"),
            substitute_user_id=substitute,
            station_leave=False,
            station_leave_details={},
            medical_evidence_ref=data.get("medical_evidence_ref", ""),
            exclude_id=parent.pk,
        )
        related = LeaveRequest.objects.create(
            user_id=actor.user_id,
            category=parent.category,
            kind="extension",
            status=workflow.AWAITING_SUBSTITUTE if substitute else workflow.UNIT_HEAD_REVIEW,
            start_date=start,
            end_date=end,
            chargeable_days=days,
            purpose=data.get("purpose", "Extension"),
            substitute_user_id=substitute,
            substitute_response="pending" if substitute else "",
            medical_evidence_ref=data.get("medical_evidence_ref", ""),
            policy_version_id=policy.pk,
            calendar_version_id=calendar.pk,
            parent_request=parent,
            submitted_at=timezone.now(),
        )
        WorkflowTask.objects.create(
            request=related,
            task_type="substitute_response" if substitute else "unit_head_review",
            assigned_user_id=substitute,
            assigned_role="Substitute / Responsibility Holder" if substitute else "Unit Head",
        )
    elif kind == "resumption":
        if parent.category not in {"EL", "COL", "VL"}:
            raise ConflictError(
                "Resumption applies to EL, COL or VL in this study baseline.",
                code="resumption_not_allowed",
            )
        if not _has(actor, "elm.request.resume"):
            raise PermissionDeniedError("This action needs elm.request.resume.")
        actual = date.fromisoformat(str(data["actual_resumption_date"]))
        if not (parent.start_date <= actual <= parent.end_date):
            raise ConflictError(
                "Actual resumption date must be within the approved leave interval.",
                code="resumption_date_invalid",
            )
        related = LeaveRequest.objects.create(
            user_id=actor.user_id,
            category=parent.category,
            kind="resumption",
            status=workflow.RESUMPTION_PENDING,
            start_date=actual,
            end_date=actual,
            chargeable_days=Decimal("0"),
            purpose=data.get("purpose", "Resumption of duty"),
            parent_request=parent,
            actual_resumption_date=actual,
            submitted_at=timezone.now(),
        )
        WorkflowTask.objects.create(
            request=related, task_type="resumption_verification", assigned_role="Unit Head"
        )
    else:
        raise ConflictError(
            "Unsupported related request type.", code="invalid_related_request_type"
        )
    _audit(
        related,
        actor,
        f"{kind}_submitted",
        "approved",
        related.status,
        payload={"parent_request_id": parent.pk},
    )
    return related


def balance_for(user_id, actor=None):
    result = {}
    today = timezone.localdate()
    for category in ENTITLEMENT_DEFAULTS:
        result[category] = str(_balance(user_id, category, today))
    return result
