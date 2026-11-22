"""Zone and gate maintenance (VMS-CFR-026 CRUD half, CFR-001 record keeping).

There is no delete: a zone or gate that exists is referenced by passes, logs
and policies, so the only removal is deactivation.
"""
from __future__ import annotations

from django.db import IntegrityError, transaction

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.vms.models import Gate, Zone
from modules.vms.services.common import audit, authz

PERM = "vms.zone.manage"


def _name(value) -> str:
    value = (value or "").strip()
    if not value:
        raise BadRequestError("name is required.", code="validation_error")
    return value


def _parent(parent_id, zone_id=None):
    if parent_id is None:
        return None
    parent = Zone.objects.filter(pk=parent_id, is_active=True).first()
    if parent is None:
        raise BadRequestError("Unknown or inactive parent zone.", code="unknown_zone")
    node = parent
    while node is not None:           # reject cycles
        if zone_id is not None and node.pk == zone_id:
            raise BadRequestError("A zone cannot be its own ancestor.",
                                  code="validation_error")
        node = node.parent_zone
    return parent


def create_zone(*, actor, name, is_restricted=False, parent_zone_id=None) -> Zone:
    authz.require(actor, PERM)
    name = _name(name)
    try:
        with transaction.atomic():
            zone = Zone.objects.create(name=name, is_restricted=bool(is_restricted),
                                       parent_zone=_parent(parent_zone_id))
            audit.record(actor=actor, action="vms.zone.created", entity=zone,
                         detail={"name": name, "is_restricted": zone.is_restricted})
    except IntegrityError:
        raise ConflictError("A zone with that name exists.", code="duplicate_name") from None
    return zone


_UNSET = object()


def update_zone(*, actor, zone_id: int, name=_UNSET, is_restricted=_UNSET,
                parent_zone_id=_UNSET, is_active=_UNSET) -> Zone:
    authz.require(actor, PERM)
    try:
        with transaction.atomic():
            zone = Zone.objects.select_for_update().filter(pk=zone_id).first()
            if zone is None:
                raise NotFoundError("Zone not found.")
            detail = {}
            if name is not _UNSET and _name(name) != zone.name:
                detail["renamed"] = [zone.name, _name(name)]
                zone.name = _name(name)
            if is_restricted is not _UNSET and bool(is_restricted) != zone.is_restricted:
                detail["is_restricted"] = [zone.is_restricted, bool(is_restricted)]
                zone.is_restricted = bool(is_restricted)
            if parent_zone_id is not _UNSET and parent_zone_id != zone.parent_zone_id:
                detail["parent_zone_id"] = [zone.parent_zone_id, parent_zone_id]
                zone.parent_zone = _parent(parent_zone_id, zone.pk)
            if is_active is not _UNSET and bool(is_active) != zone.is_active:
                in_use = (zone.gates.filter(is_active=True).exists()
                          or zone.children.filter(is_active=True).exists())
                if not is_active and in_use:
                    raise ConflictError(
                        "Deactivate the zone's gates and child zones first.",
                        code="zone_in_use")
                detail["is_active"] = [zone.is_active, bool(is_active)]
                zone.is_active = bool(is_active)
            if detail:
                zone.save()
                audit.record(actor=actor, action="vms.zone.updated", entity=zone,
                             detail=detail)
    except IntegrityError:
        raise ConflictError("A zone with that name exists.", code="duplicate_name") from None
    return zone


def create_gate(*, actor, name, zone_id: int, device_id="") -> Gate:
    authz.require(actor, PERM)
    name = _name(name)
    zone = Zone.objects.filter(pk=zone_id, is_active=True).first()
    if zone is None:
        raise BadRequestError("Unknown or inactive zone.", code="unknown_zone")
    try:
        with transaction.atomic():
            gate = Gate.objects.create(name=name, zone=zone, device_id=device_id or "")
            audit.record(actor=actor, action="vms.gate.created", entity=gate,
                         detail={"name": name, "zone_id": zone.pk})
    except IntegrityError:
        raise ConflictError("A gate with that name exists.", code="duplicate_name") from None
    return gate


def update_gate(*, actor, gate_id: int, name=_UNSET, zone_id=_UNSET,
                device_id=_UNSET, is_active=_UNSET) -> Gate:
    authz.require(actor, PERM)
    try:
        with transaction.atomic():
            gate = Gate.objects.select_for_update().filter(pk=gate_id).first()
            if gate is None:
                raise NotFoundError("Gate not found.")
            detail = {}
            if name is not _UNSET and _name(name) != gate.name:
                detail["renamed"] = [gate.name, _name(name)]
                gate.name = _name(name)
            if zone_id is not _UNSET and zone_id != gate.zone_id:
                zone = Zone.objects.filter(pk=zone_id, is_active=True).first()
                if zone is None:
                    raise BadRequestError("Unknown or inactive zone.", code="unknown_zone")
                detail["zone_id"] = [gate.zone_id, zone.pk]
                gate.zone = zone
            if device_id is not _UNSET and device_id != gate.device_id:
                detail["device_id"] = [gate.device_id, device_id]
                gate.device_id = device_id
            if is_active is not _UNSET and bool(is_active) != gate.is_active:
                detail["is_active"] = [gate.is_active, bool(is_active)]
                gate.is_active = bool(is_active)
            if detail:
                gate.save()
                audit.record(actor=actor, action="vms.gate.updated", entity=gate,
                             detail=detail)
    except IntegrityError:
        raise ConflictError("A gate with that name exists.", code="duplicate_name") from None
    return gate


UNSET = _UNSET
