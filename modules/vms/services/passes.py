"""Pass issuance and deactivation.

VMS-BR-020: no duplicate pass for the same visitor on the same day — the
day's window is the pass's local calendar day, checked against every pass
already issued (active or not) for that visitor.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from django.utils import timezone

from modules.vms.models import Pass, Visitor
from modules.vms.services import policies
from modules.vms.services.errors import DuplicatePassError, PassStateError


def _day_window(day) -> tuple:
    start = timezone.make_aware(datetime.combine(day, datetime.min.time()))
    end = start + timedelta(days=1)
    return start, end


def has_pass_today(visitor_id: int, day=None) -> bool:
    """VMS-BR-020: any pass already issued for this visitor that day."""
    day = day or timezone.localdate()
    start, end = _day_window(day)
    return Pass.objects.filter(visitor_id=visitor_id,
                               valid_from__gte=start,
                               valid_from__lt=end).exists()


def issue_pass(*, visit_id: int, visitor_id: int, pass_type: str,
               permitted_zones: list[str] | None = None,
               issued_by_user_id: int | None = None,
               parent_pass_id: int | None = None,
               valid_from=None, reviewed_by_user_id: int | None = None,
               is_event_fast_lane: bool = False,
               otp: str = "") -> Pass:
    """Create today's pass, refusing a second one (VMS-BR-020).

    VMS-BR-035: a SAFE_LIST pass carries the security reviewer's id — the
    safe-list alone never issues a pass without that review.
    """
    if has_pass_today(visitor_id):
        raise DuplicatePassError(
            "This visitor already has a pass issued today.",
            details=[{"visitor_id": visitor_id}])
    policy = policies.effective()
    valid_from = valid_from or timezone.now()
    hours = policies.pass_duration_hours(policy, pass_type)
    visitor = Visitor.objects.filter(pk=visitor_id).first()
    anonymous = visitor is not None and visitor.is_anonymous
    code = "" if anonymous else _new_code()          # VMS-BR-013 no QR
    return Pass.objects.create(
        visit_id=visit_id, visitor_id=visitor_id, pass_type=pass_type,
        pass_code=code or f"ANON-{secrets.token_hex(6)}",
        otp=otp or (secrets.randbelow(900000) + 100000 if anonymous else ""),
        valid_from=valid_from,
        valid_until=policies.valid_until(valid_from, hours),
        permitted_zones=list(permitted_zones or []),
        issued_by_user_id=issued_by_user_id,
        parent_pass_id=parent_pass_id,
        reviewed_by_user_id=reviewed_by_user_id,
        is_event_fast_lane=is_event_fast_lane)


def _new_code() -> str:
    return secrets.token_urlsafe(16).replace("-", "")[:24]


def deactivate_pass(pass_obj: Pass, *, reason: str,
                    actor_user_id: int | None = None) -> Pass:
    """Early deactivation for policy-breach handling. Deliberately sends NO
    host notification — VMS-BR-047: no host notification if the pass is
    rejected."""
    if pass_obj.status != "ACTIVE":
        raise PassStateError(f"Pass is {pass_obj.status}, not active.")
    pass_obj.status = "DEACTIVATED"
    pass_obj.deactivated_at = timezone.now()
    pass_obj.deactivation_reason = reason
    pass_obj.save(update_fields=["status", "deactivated_at",
                                 "deactivation_reason", "updated_at"])
    return pass_obj


def find_pass(code: str) -> Pass | None:
    if not code:
        return None
    return Pass.objects.filter(pass_code=code).first()


def pass_is_live(pass_obj: Pass, at=None) -> bool:
    """Active, and inside its validity window. A null valid_until is
    real-time (VMS-BR-016) and therefore always inside the window."""
    if pass_obj.status != "ACTIVE":
        return False
    at = at or timezone.now()
    if at < pass_obj.valid_from:
        return False
    if pass_obj.valid_until and at > pass_obj.valid_until:
        return False
    return True


def expire_if_due(pass_obj: Pass, at=None) -> Pass:
    """Flip an ACTIVE-but-lapsed pass to EXPIRED (auto-checkout support)."""
    at = at or timezone.now()
    if (pass_obj.status == "ACTIVE" and pass_obj.valid_until
            and at > pass_obj.valid_until):
        pass_obj.status = "EXPIRED"
        pass_obj.save(update_fields=["status", "updated_at"])
    return pass_obj
