"""Visitor registration: pre-registration requests and walk-ins.

VMS-BR-011  the blacklist check runs on BOTH paths — request and walk-in.
VMS-BR-013  an anonymous visitor never gets a QR identity.
VMS-BR-015  safe-list status grants no zones; only expedited review.
VMS-BR-017  a same-day visitor with no pass is handled, not doubled.
VMS-BR-020  one pass per visitor per day (see services.passes).
VMS-BR-024  an active blacklist match blocks the registration request.
VMS-BR-025  a misconfigured security person invalidates the visit.
"""
from __future__ import annotations

import uuid

from django.utils import timezone

from core.api.exceptions import ConflictError
from modules.vms.models import Pass, Visit, Visitor, VisitRequest, normalize_id
from modules.vms.services import blacklist as blacklist_service
from modules.vms.services import notifications, policies, roles
from modules.vms.services.errors import DuplicatePassError, VmsError
from modules.vms.services.passes import has_pass_today, issue_pass


class VisitorDisabledError(VmsError):
    """VMS-BR-027's consequence: a denied visit disables the visitor, and a
    disabled visitor cannot be registered again."""

    code = "visitor_disabled"
    status_code = 403
    message = "This visitor is disabled."


def create_visitor(*, full_name: str, phone: str = "", email: str = "",
                   id_doc_type: str = "OTHER", id_doc_number: str = "",
                   photo_url: str = "", is_anonymous: bool = False,
                   user_id: int | None = None,
                   created_by_user_id: int | None = None) -> Visitor:
    return Visitor.objects.create(
        full_name=full_name.strip(), phone=phone.strip(),
        email=email.strip(), id_doc_type=id_doc_type,
        id_doc_number=id_doc_number.strip(),
        id_doc_normalized=("" if is_anonymous
                           else normalize_id(id_doc_number)),
        photo_url=photo_url, is_anonymous=is_anonymous, user_id=user_id,
        created_by_user_id=created_by_user_id)


def _guard_disabled(visitor: Visitor) -> None:
    if visitor.is_disabled:
        raise VisitorDisabledError(
            visitor.disabled_reason or "This visitor is disabled.")


def create_visit_request(*, visitor: Visitor, host_user_id: int,
                         purpose: str, requested_start=None,
                         requested_end=None,
                         requested_zones: list[str] | None = None,
                         instructions: str = "",
                         host_contact_email: str = "",
                         host_contact_phone: str = "",
                         is_shared_badge: bool = False,
                         source: str = "PRE_REGISTERED",
                         created_by_user_id: int | None = None,
                         ) -> tuple[VisitRequest, list]:
    """A pending pre-registration. VMS-BR-011/024: the blacklist check runs
    here, before anything is stored as pending. VMS-BR-007: the original
    request id is minted once and every notification carries it.
    VMS-BR-012: shared badge or not, the host is notified.
    """
    _guard_disabled(visitor)
    blacklist_service.assert_registration_allowed(
        visitor, context="visit request")                  # BR-011 / BR-024

    request = VisitRequest.objects.create(
        visitor_id=visitor.id, host_user_id=host_user_id,
        host_contact_email=host_contact_email,
        host_contact_phone=host_contact_phone,
        purpose=purpose, requested_start=requested_start,
        requested_end=requested_end,
        requested_zones=list(requested_zones or []),
        source=source, instructions=instructions,
        original_request_id=uuid.uuid4().hex,               # BR-007
        approval_expires_at=policies.approval_deadline(),   # BR-014 timeout
        is_shared_badge=is_shared_badge,
        created_by_user_id=created_by_user_id)
    notes = notifications.notify_host(
        request, kind="VISIT_REQUEST", subject="New visit request",
        payload={"purpose": purpose})                       # BR-012
    return request, notes


def register_walk_in(*, visitor: Visitor | None, host_user_id: int,
                     purpose: str, actor,
                     gate_code: str = "", machine_id: str = "",
                     zones: list[str] | None = None,
                     ) -> tuple[Visit, Pass]:
    """Security registers a guest at the gate (VMS-UC-022).

    Order matters: the security assignment is checked before any row is
    written (VMS-BR-025), the blacklist check before the visit is created
    (VMS-BR-011/024), and the same-day rules decide whether this is a new
    visit or a pass on the visit that is already there (VMS-BR-017/020).
    """
    roles.require_security(actor, gate_code=gate_code)      # BR-025
    if visitor is None:
        raise VmsError("A walk-in needs a visitor record.",
                       code="visitor_required")
    _guard_disabled(visitor)
    blacklist_service.assert_registration_allowed(
        visitor, context="walk-in registration")            # BR-011 / BR-024

    today = timezone.localdate()
    existing = (Visit.objects
                .filter(visitor_id=visitor.id,
                        checked_in_at__date=today)
                .order_by("-id")
                .first())
    if existing is not None and not has_pass_today(visitor.id, today):
        # BR-017: same-day visitor who never got a pass — handle the
        # duplicate by issuing the pass on the visit that already exists.
        if existing.status in ("COMPLETED", "TERMINATED", "INVALIDATED"):
            raise ConflictError(
                "This visitor already has a closed visit today.",
                code="duplicate_visit")
        pass_obj = _issue_for_walk_in(existing, visitor, actor, zones)
        return existing, pass_obj
    if has_pass_today(visitor.id, today):
        raise DuplicatePassError(
            "This visitor already has a pass today.",
            details=[{"visitor_id": visitor.id}])           # BR-020

    visit = Visit.objects.create(
        visitor_id=visitor.id, host_user_id=host_user_id,
        purpose=purpose, status="SCHEDULED", source="WALK_IN",
        is_walk_in=True, gate_code=gate_code,
        created_by_user_id=getattr(actor, "user_id", None))
    pass_obj = _issue_for_walk_in(visit, visitor, actor, zones)
    return visit, pass_obj


def _issue_for_walk_in(visit: Visit, visitor: Visitor, actor,
                       zones: list[str] | None) -> Pass:
    safe = blacklist_service.is_safe_listed(visitor)        # BR-035 review
    return issue_pass(
        visit_id=visit.id, visitor_id=visitor.id,
        pass_type="WALK_IN",
        permitted_zones=list(zones or []),
        issued_by_user_id=getattr(actor, "user_id", None),
        reviewed_by_user_id=getattr(actor, "user_id", None) if safe else None)
