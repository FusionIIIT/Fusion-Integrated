"""Who sees which rows, decided once (AFR-VH-109).

Every list and detail view starts from a queryset built here. A row outside
scope is simply absent, so a foreign id is a 404 rather than a 403 that would
confirm the booking exists.

    Indenter      their own bookings only (AFR-VH-001..003)
    Caretaker     every booking, online and offline (UC-VH-003, UC-VH-005)
    VH In-Charge  every booking (PS 2.3 "views online and offline records")
"""
from __future__ import annotations

from django.db.models import QuerySet

from modules.visitor_hostel.domain import permissions as perms
from modules.visitor_hostel.models import (
    Bill,
    Booking,
    InventoryItem,
    ReplenishmentRequirement,
    StayAlert,
)

OPERATOR_BOOKING_PERMISSIONS = (perms.BOOKING_VIEW, perms.BOOKING_REVIEW, perms.BOOKING_APPROVE)


def _has(actor, *codes: str) -> bool:
    check = getattr(actor, "has_permission", None)
    return bool(check) and any(check(c) for c in codes)


def _own_id(actor) -> int | None:
    return getattr(actor, "user_id", None)


def sees_all_bookings(actor) -> bool:
    return _has(actor, *OPERATOR_BOOKING_PERMISSIONS)


def bookings_for(actor) -> QuerySet[Booking]:
    base = Booking.objects.all()
    if sees_all_bookings(actor):
        return base
    own = _own_id(actor)
    if own is None or not _has(actor, perms.BOOKING_VIEW_SELF):
        return base.none()
    return base.filter(indenter_user_id=own)


def bookings_detailed(actor) -> QuerySet[Booking]:
    """The detail view's shape: every relation the serializer follows, prefetched."""
    return (bookings_for(actor)
            .select_related("cancellation", "bill")
            .prefetch_related("allotments__room", "meals", "modifications",
                              "transitions", "alerts", "bill__lines"))


def bills_for(actor) -> QuerySet[Bill]:
    base = Bill.objects.select_related("booking").prefetch_related("lines")
    if _has(actor, perms.BILL_MANAGE, perms.BILL_VIEW):
        return base
    own = _own_id(actor)
    if own is None or not _has(actor, perms.BOOKING_VIEW_SELF):
        return base.none()
    return base.filter(booking__indenter_user_id=own)


def inventory_for(actor) -> QuerySet[InventoryItem]:
    if _has(actor, perms.INVENTORY_MANAGE, perms.INVENTORY_VIEW):
        return InventoryItem.objects.all()
    return InventoryItem.objects.none()


def replenishments_for(actor) -> QuerySet[ReplenishmentRequirement]:
    base = ReplenishmentRequirement.objects.select_related("item")
    if _has(actor, perms.REPLENISHMENT_CREATE, perms.REPLENISHMENT_APPROVE,
            perms.INVENTORY_VIEW):
        return base
    return base.none()


def stay_alerts_for(actor) -> QuerySet[StayAlert]:
    base = StayAlert.objects.select_related("booking")
    if _has(actor, perms.ALERT_VIEW, perms.OPERATIONS_REPORT_VIEW):
        return base
    return base.none()
