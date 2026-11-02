"""VIP permissions (VMS-UC-003, CFR-004, BR-196/197, D-6, D-16).

A Super Admin grants a per-visitor override scope (zones + validity window).
Expiry is mandatory. A restricted zone is only included when it is explicitly
confirmed in ``restricted_zone_ids``.
"""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.vms.models import VipPermission, Visitor, Zone
from modules.vms.services.common import audit, authz

PERM = "vms.vip.manage"


def _zones(zone_ids, restricted_zone_ids) -> list[Zone]:
    ids = set(zone_ids or [])
    zones = list(Zone.objects.filter(pk__in=ids, is_active=True))
    if len(zones) != len(ids):
        raise BadRequestError("Unknown or inactive zone.", code="unknown_zone")
    confirmed = set(restricted_zone_ids or [])
    bad = sorted(z.pk for z in zones if z.is_restricted and z.pk not in confirmed)
    if bad:
        raise BadRequestError(
            "Restricted zones must be listed explicitly in restricted_zone_ids.",
            code="restricted_zone_not_confirmed", details=[{"zone_ids": bad}])
    stray = confirmed - ids
    if stray:
        raise BadRequestError("restricted_zone_ids must be a subset of zone_ids.",
                              code="validation_error")
    return zones


def _visitor(*, visitor_id, id_doc_type, id_doc_number, full_name, phone, email) -> Visitor:
    if visitor_id:
        visitor = Visitor.objects.filter(pk=visitor_id).first()
        if visitor is None:
            raise NotFoundError("No such visitor.")
        return visitor
    if not id_doc_number or not id_doc_type:
        raise BadRequestError("id_doc_type and id_doc_number are required.",
                              code="validation_error")
    visitor = Visitor.objects.filter(id_doc_number=id_doc_number,
                                     id_doc_type=id_doc_type).first()
    if visitor is not None:
        return visitor
    if not full_name:
        raise BadRequestError("full_name is required for a new visitor.",
                              code="validation_error")
    return Visitor.objects.create(full_name=full_name, phone=phone or "",
                                  email=email or "", id_doc_type=id_doc_type,
                                  id_doc_number=id_doc_number)


def grant(*, actor, valid_until, valid_from=None, zone_ids=(), restricted_zone_ids=(),
          visitor_id=None, id_doc_type="", id_doc_number="", full_name="",
          phone="", email="") -> VipPermission:
    authz.require(actor, PERM)
    now = timezone.now()
    valid_from = valid_from or now
    if valid_until is None:
        raise BadRequestError("A VIP permission needs an expiry.", code="validation_error")
    if valid_until <= valid_from or valid_until <= now:
        raise BadRequestError("valid_until must be in the future and after valid_from.",
                              code="validation_error")
    zones = _zones(zone_ids, restricted_zone_ids)
    with transaction.atomic():
        visitor = _visitor(visitor_id=visitor_id, id_doc_type=id_doc_type,
                           id_doc_number=id_doc_number, full_name=full_name,
                           phone=phone, email=email)
        list(Visitor.objects.select_for_update().filter(pk=visitor.pk))
        if VipPermission.objects.filter(
                visitor=visitor, revoked_at__isnull=True,
                valid_from__lt=valid_until, valid_until__gt=valid_from).exists():
            raise ConflictError("The visitor already has an overlapping VIP permission.",
                                code="overlapping_vip")
        vip = VipPermission.objects.create(
            visitor=visitor, valid_from=valid_from, valid_until=valid_until,
            granted_by_user_id=actor.user_id)
        vip.zones.set(zones)
        audit.record(actor=actor, action="vms.vip.granted", entity=vip, detail={
            "visitor_id": visitor.pk, "zone_ids": sorted(z.pk for z in zones),
            "valid_from": valid_from.isoformat(), "valid_until": valid_until.isoformat()})
    return vip


def revoke(*, actor, vip_id: int) -> VipPermission:
    authz.require(actor, PERM)
    with transaction.atomic():
        vip = VipPermission.objects.select_for_update().filter(pk=vip_id).first()
        if vip is None:
            raise NotFoundError("No such VIP permission.")
        if vip.revoked_at is not None:
            raise ConflictError("Already revoked.", code="already_revoked")
        vip.revoked_at = timezone.now()
        vip.save(update_fields=["revoked_at"])
        audit.record(actor=actor, action="vms.vip.revoked", entity=vip,
                     detail={"visitor_id": vip.visitor_id})
    return vip


def list_permissions(*, actor, active_only: bool = False):
    authz.require(actor, PERM)
    qs = VipPermission.objects.select_related("visitor").prefetch_related("zones")
    if active_only:
        now = timezone.now()
        qs = qs.filter(revoked_at__isnull=True, valid_from__lte=now, valid_until__gt=now)
    return qs.order_by("-id")
