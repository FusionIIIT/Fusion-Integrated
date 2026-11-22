"""Visitor and visit registration services."""

from __future__ import annotations

import uuid
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from modules.vms.domain.blacklist import is_blacklisted
from modules.vms.domain.qr_crypto import generate_qr_token
from modules.vms.domain.validation import (
    validate_advance_window,
    validate_mandatory_visitor_fields,
    validate_visit_duration,
    validate_visiting_hours,
)
from modules.vms.models import HostPreAuthorization, Pass, Visitor, VisitRequest
from modules.vms.selectors.blacklist import get_active_blacklist_candidates
from modules.vms.selectors.policy import get_active_published_policy


class DuplicateVisitError(ValueError):
    """Raised when an overlapping visit is already booked."""


class BlacklistViolationError(PermissionError):
    """Raised when visitor is blocked on blacklist."""


@transaction.atomic
def pre_register_visit(
    name: str,
    email: str,
    phone: str,
    host_id: int,
    purpose: str,
    scheduled_start: datetime,
    scheduled_end: datetime,
    id_document_type: str,
    id_document_number: str,
    organization: str = "",
    access_zones: list[str] | None = None,
    is_urgent_exception: bool = False,
    external_event_ref: str = "",
) -> VisitRequest:
    """Pre-register an external visit with full domain validation."""
    now = timezone.now()

    # 1. Mandatory fields
    validate_mandatory_visitor_fields(
        name=name,
        email=email,
        phone=phone,
        host_id=host_id,
        purpose=purpose,
        id_document_type=id_document_type,
        id_document_number=id_document_number,
    )

    # 2. Advance window (BR-202 / BR-203)
    validate_advance_window(scheduled_start, now, is_urgent_exception=is_urgent_exception)

    # 3. Visit duration (BR-193)
    policy = get_active_published_policy()
    max_duration = policy.max_duration_hours if policy else 12
    validate_visit_duration(scheduled_start, scheduled_end, max_duration_hours=max_duration)

    # 4. Visiting hours
    if policy:
        validate_visiting_hours(
            scheduled_start, policy.visiting_hours_start, policy.visiting_hours_end
        )

    # 5. Blacklist validation (BR-051 / BR-112)
    candidates = get_active_blacklist_candidates()
    blocked, reason = is_blacklisted(name, id_document_number, phone, candidates, now)
    if blocked:
        raise BlacklistViolationError(f"Registration rejected due to blacklist match: {reason}")

    # 6. Duplicate visit check (BR-038)
    loc_date = timezone.localtime(scheduled_start).date()
    start_of_day = timezone.datetime.combine(
        loc_date, timezone.datetime.min.time(), tzinfo=timezone.get_current_timezone()
    )
    end_of_day = timezone.datetime.combine(
        loc_date, timezone.datetime.max.time(), tzinfo=timezone.get_current_timezone()
    )
    existing_duplicate = VisitRequest.objects.filter(
        visitor__id_document_number=id_document_number,
        scheduled_start__gte=start_of_day,
        scheduled_start__lte=end_of_day,
        status__in=["PENDING_APPROVAL", "APPROVED", "CHECKED_IN"],
    ).exists()
    if existing_duplicate:
        raise DuplicateVisitError(
            "A visit request is already active or pending for this visitor on the selected date."
        )

    # 7. Create or get Visitor
    visitor, _ = Visitor.objects.get_or_create(
        id_document_number=id_document_number,
        defaults={
            "name": name,
            "email": email,
            "phone": phone,
            "organization": organization,
            "id_document_type": id_document_type,
        },
    )

    # 8. Check pre-authorizations (BR-195) and VIP override (BR-196, BR-197)
    today = now.date()
    has_preauth = HostPreAuthorization.objects.filter(
        host_id=host_id,
        visitor_email=email,
        valid_from__lte=today,
        valid_to__gte=today,
        is_active=True,
    ).exists()

    is_vip = visitor.is_vip

    initial_status = "PENDING_APPROVAL"
    pass_type = "PRE_REGISTERED"
    if is_vip:
        initial_status = "APPROVED"
        pass_type = "VIP"
    elif has_preauth:
        initial_status = "APPROVED"

    visit = VisitRequest.objects.create(
        visitor=visitor,
        host_id=host_id,
        purpose=purpose,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
        status=initial_status,
        pass_type=pass_type,
        access_zones=access_zones or ["Main Gate"],
        is_urgent_exception=is_urgent_exception,
        external_event_ref=external_event_ref,
    )

    # If auto-approved, issue pass immediately
    if initial_status == "APPROVED":
        pass_number = f"PASS-{uuid.uuid4().hex[:8].upper()}"
        qr_token = generate_qr_token(pass_number)
        Pass.objects.create(
            visit_request=visit,
            pass_number=pass_number,
            qr_token=qr_token,
            pass_type=pass_type,
            valid_from=scheduled_start,
            valid_to=scheduled_end,
            status="ACTIVE",
        )

    return visit


@transaction.atomic
def walk_in_register(
    name: str,
    email: str,
    phone: str,
    host_id: int,
    purpose: str,
    id_document_type: str,
    id_document_number: str,
    operator_id: int | None = None,
    organization: str = "",
    duration_hours: int = 4,
    auto_approve: bool = False,
) -> VisitRequest:
    """Register an unscheduled walk-in visitor at security gate (UC-017, BR-053)."""
    now = timezone.now()
    scheduled_end = now + timezone.timedelta(hours=min(duration_hours, 8))

    # Blacklist check
    candidates = get_active_blacklist_candidates()
    blocked, reason = is_blacklisted(name, id_document_number, phone, candidates, now)
    if blocked:
        raise BlacklistViolationError(f"Walk-in rejected due to blacklist match: {reason}")

    visitor, _ = Visitor.objects.get_or_create(
        id_document_number=id_document_number,
        defaults={
            "name": name,
            "email": email,
            "phone": phone,
            "organization": organization,
            "id_document_type": id_document_type,
        },
    )

    status = "APPROVED" if auto_approve else "PENDING_APPROVAL"

    visit = VisitRequest.objects.create(
        visitor=visitor,
        host_id=host_id,
        purpose=purpose,
        scheduled_start=now,
        scheduled_end=scheduled_end,
        status=status,
        pass_type="WALK_IN",
        access_zones=["Main Gate"],
    )

    if status == "APPROVED":
        pass_number = f"WALK-{uuid.uuid4().hex[:8].upper()}"
        qr_token = generate_qr_token(pass_number)
        Pass.objects.create(
            visit_request=visit,
            pass_number=pass_number,
            qr_token=qr_token,
            pass_type="WALK_IN",
            valid_from=now,
            valid_to=scheduled_end,
            status="ACTIVE",
        )

    return visit


@transaction.atomic
def bulk_register_visitors(
    records: list[dict],
    host_id: int,
    purpose: str,
    scheduled_start: datetime,
    scheduled_end: datetime,
    external_event_ref: str = "",
) -> list[VisitRequest]:
    """Bulk register event visitors (UC-008, BW-VMS-21)."""
    created_visits = []
    for r in records:
        visit = pre_register_visit(
            name=r["name"],
            email=r["email"],
            phone=r["phone"],
            host_id=host_id,
            purpose=purpose,
            scheduled_start=scheduled_start,
            scheduled_end=scheduled_end,
            id_document_type=r.get("id_document_type", "OTHER"),
            id_document_number=r["id_document_number"],
            organization=r.get("organization", ""),
            access_zones=r.get("access_zones", ["Main Gate", "Event Hall"]),
            is_urgent_exception=True,
            external_event_ref=external_event_ref,
        )
        created_visits.append(visit)
    return created_visits
