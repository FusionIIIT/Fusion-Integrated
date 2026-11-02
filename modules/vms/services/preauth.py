"""Host pre-authorisation of repeat visitors (VMS-CFR-011, UC-014, BR-195).

Use of a pre-authorisation (skip host approval, `used_visits += 1`) happens in
`registration.submit`; this module manages the grants themselves.
"""
from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.vms.models import PreAuthorization, Zone
from modules.vms.services import blacklist, policy, registration
from modules.vms.services.common import audit, authz

MAX_VALIDITY = timedelta(days=365)
MAX_VISITS_CAP = 100


def create(*, host_actor, data: dict) -> PreAuthorization:
    """`data`: visitor fields (full_name, phone, email, id_doc_type, id_doc_number),
    zones, valid_from, valid_until, max_visits."""
    if not authz.is_host(host_actor):
        raise PermissionDeniedError()
    for f in ("full_name", "phone", "id_doc_type", "id_doc_number"):
        if not str(data.get(f) or "").strip():
            raise BadRequestError(f"{f} is required.", code="missing_fields")
    registration.validate_id_document(data["id_doc_type"], data["id_doc_number"])
    now = timezone.now()
    valid_from = data.get("valid_from") or now
    valid_until = data["valid_until"]
    if valid_until <= valid_from or valid_until <= now:
        raise BadRequestError("valid_until must be in the future and after valid_from.",
                              code="invalid_window")
    if valid_until > now + MAX_VALIDITY:
        raise BadRequestError("A pre-authorisation may last at most one year.",
                              code="validity_too_long")
    max_visits = int(data.get("max_visits") or 1)
    if not 1 <= max_visits <= MAX_VISITS_CAP:
        raise BadRequestError(f"max_visits must be between 1 and {MAX_VISITS_CAP}.",
                              code="invalid_max_visits")
    zones = list(data.get("zones") or [])
    zone_ids = {z.pk if hasattr(z, "pk") else int(z) for z in zones}
    if zone_ids:
        pol = policy.effective()
        found = set(Zone.objects.filter(pk__in=zone_ids, is_active=True)
                    .values_list("pk", flat=True))
        if found != zone_ids:
            raise BadRequestError("A zone does not exist or is inactive.", code="invalid_zone")
        if zone_ids & pol.restricted_zone_ids:
            raise BadRequestError("Restricted zones cannot be pre-authorised.",
                                  code="zone_not_allowed")
    hit = blacklist.check(
        checkpoint="pre_registration", name=data["full_name"],
        id_doc_number=data["id_doc_number"], phone=data["phone"],
        email=data.get("email", ""))
    if hit is not None:
        with transaction.atomic():
            registration.record_blacklist_hit(actor=host_actor, hit=hit,
                                              visitor_label=data["full_name"])
        raise BadRequestError("This visitor cannot be pre-authorised.",
                              code="visitor_blacklisted")
    with transaction.atomic():
        visitor = registration.resolve_visitor(
            session_visitor=None, data=data, update_existing=False)
        pa = PreAuthorization.objects.create(
            host_user_id=host_actor.user_id, visitor=visitor, valid_from=valid_from,
            valid_until=valid_until, max_visits=max_visits)
        pa.zones.set(zone_ids)
        audit.record(actor=host_actor, action="vms.preauth.created", entity=pa,
                     detail={"visitor_id": visitor.pk, "zones": sorted(zone_ids),
                             "max_visits": max_visits,
                             "valid_until": valid_until.isoformat()})
    return pa


def revoke(*, host_actor, preauth_id: int) -> PreAuthorization:
    """Owner-only (others get 404). Revoking twice is a conflict."""
    with transaction.atomic():
        pa = (PreAuthorization.objects.select_for_update()
              .filter(pk=preauth_id, host_user_id=host_actor.user_id).first())
        if pa is None:
            raise NotFoundError()
        if pa.revoked_at is not None:
            raise ConflictError("Already revoked.", code="already_revoked")
        pa.revoked_at = timezone.now()
        pa.save(update_fields=["revoked_at"])
        audit.record(actor=host_actor, action="vms.preauth.revoked", entity=pa)
    return pa

