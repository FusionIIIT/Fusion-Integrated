"""VMS Registration and Pass Issuance Service.
Enforces BR-001, BR-004, BR-017, BR-020, BR-032.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from modules.vms.domain.rules import (
    calculate_walk_in_duration,
    validate_blacklist_match,
    validate_same_day_pass,
)
from modules.vms.domain.state_machine import TransitionTrigger
from modules.vms.models.access import GateAlert
from modules.vms.models.visitors import BlacklistEntry, Visitor
from modules.vms.models.visits import Visit
from modules.vms.services.errors import (
    BlacklistMatchError,
    DuplicatePassError,
)
from modules.vms.services.gate import transition_visit_state


def _hash_id_number(id_number: str) -> str:
    cleaned = id_number.strip().upper()
    return hashlib.sha256(cleaned.encode("utf-8")).hexdigest()


def get_or_create_visitor(
    first_name: str,
    last_name: str,
    phone: str,
    email: str,
    id_type: str,
    id_number: str,
    organization: str = "",
) -> Visitor:
    id_hash = _hash_id_number(id_number)
    visitor, _ = Visitor.objects.get_or_create(
        id_number_hash=id_hash,
        defaults={
            "first_name": first_name.strip(),
            "last_name": last_name.strip(),
            "phone": phone.strip(),
            "email": email.strip().lower(),
            "id_type": id_type,
            "organization": organization.strip(),
        },
    )
    return visitor


@transaction.atomic
def request_or_create_visit(
    visitor_data: dict,
    host_user_id: int,
    purpose: str,
    valid_from: datetime,
    valid_to: datetime,
    allowed_zones: list[str] | None = None,
    visit_type: str = "pre_registered",
    is_multi_entry: bool = False,
    creator_user_id: int | None = None,
) -> Visit:
    """Creates a visit request or issues a walk-in pass."""
    id_hash = _hash_id_number(visitor_data["id_number"])
    phone = visitor_data.get("phone", "").strip()
    full_name = f"{visitor_data.get('first_name', '')} {visitor_data.get('last_name', '')}".strip()

    # Rule BR-001 & BR-004: Blacklist enforcement
    active_bl = list(
        BlacklistEntry.objects.filter(is_active=True).values(
            "id_number_hash", "phone", "full_name", "reason", "severity", "is_active"
        )
    )
    bl_check = validate_blacklist_match(id_hash, phone, full_name, active_bl)
    if bl_check.is_blacklisted:
        # Generate critical alert
        GateAlert.objects.create(
            alert_type="blacklist_registration_attempt",
            severity="critical",
            message=(
                f"Attempted registration for blacklisted person: "
                f"{full_name} ({phone}) - {bl_check.reason}"
            ),
        )
        raise BlacklistMatchError(f"Registration refused: {bl_check.reason}")

    # Rule BR-017 & BR-020: Duplicate same-day active pass check
    req_date_str = valid_from.strftime("%Y-%m-%d")
    existing_active = Visit.objects.filter(
        visitor__id_number_hash=id_hash,
        status__in=["requested", "approved", "on_site"],
    ).values_list("valid_from", flat=True)
    existing_dates = [d.strftime("%Y-%m-%d") for d in existing_active]

    pass_allowance = validate_same_day_pass(req_date_str, existing_dates)
    if not pass_allowance.allowed:
        raise DuplicatePassError(pass_allowance.reason)

    # Rule BR-032: Walk-in duration calculation
    if visit_type == "walk_in":
        now = timezone.now()
        valid_from, valid_to = calculate_walk_in_duration(now)

    visitor = get_or_create_visitor(
        first_name=visitor_data["first_name"],
        last_name=visitor_data["last_name"],
        phone=phone,
        email=visitor_data.get("email", ""),
        id_type=visitor_data.get("id_type", "aadhaar"),
        id_number=visitor_data["id_number"],
        organization=visitor_data.get("organization", ""),
    )

    pass_num = f"PASS-{timezone.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    qr_hash = hashlib.sha256(f"{pass_num}:{visitor.id}:{uuid.uuid4()}".encode()).hexdigest()

    zones = allowed_zones or ["MAIN_GATE", "ADMIN_BLOCK"]
    initial_status = "approved" if visit_type == "walk_in" else "requested"

    return Visit.objects.create(
        visitor=visitor,
        host_user_id=host_user_id,
        purpose=purpose.strip(),
        visit_type=visit_type,
        status=initial_status,
        pass_number=pass_num,
        qr_code_hash=qr_hash,
        valid_from=valid_from,
        valid_to=valid_to,
        allowed_zones=zones,
        is_multi_entry=is_multi_entry,
    )


def approve_visit(visit_id: int, host_user_id: int) -> Visit:
    """Host approves a pending visit request."""
    return transition_visit_state(
        visit_id=visit_id,
        trigger=TransitionTrigger.HOST_APPROVE,
        actor_id=host_user_id,
    )


def reject_visit(visit_id: int, host_user_id: int, reason: str = "") -> Visit:
    """Host rejects a pending visit request."""
    return transition_visit_state(
        visit_id=visit_id,
        trigger=TransitionTrigger.HOST_REJECT,
        actor_id=host_user_id,
        note=reason,
    )
