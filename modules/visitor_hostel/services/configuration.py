"""Rooms and tariffs (UC-VH-008 room records, UC-VH-011).

Tariffs are effective-dated and never edited (BR-VH-024). `actor=None` is an
operator at the command line; the tariff authority is unresolved by the spec,
so over HTTP it needs a code no designation holds yet.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.visitor_hostel.domain import meals, tariffs
from modules.visitor_hostel.domain import permissions as perms
from modules.visitor_hostel.domain import state_machine as sm
from modules.visitor_hostel.models import MealTariff, Room, RoomTariff
from modules.visitor_hostel.services import authz


def _not_backdated(exists: bool, effective_from: date) -> None:
    """A first tariff may start whenever; a replacement only from today on, so
    nobody quietly reprices stays already under way."""
    if exists and effective_from < timezone.localdate():
        raise BadRequestError(
            "A replacement tariff cannot take effect in the past.",
            code="tariff_backdated")


@transaction.atomic
def add_room_tariff(*, category: str, occupancy: str, rate: Decimal,
                    effective_from: date, actor=None) -> RoomTariff:
    if actor is not None:
        authz.require(actor, perms.TARIFF_MANAGE)
    try:
        tariffs.room_key(category, occupancy)
    except ValueError as exc:
        raise BadRequestError(str(exc), code="invalid_tariff") from exc
    if rate < 0:
        raise BadRequestError("A rate cannot be negative.", code="invalid_tariff")
    _not_backdated(RoomTariff.objects.filter(category=category, occupancy=occupancy)
                   .exists(), effective_from)
    try:
        with transaction.atomic():
            return RoomTariff.objects.create(
                category=category, occupancy=occupancy, rate_per_day=rate,
                effective_from=effective_from,
                created_by_user_id=getattr(actor, "user_id", None))
    except IntegrityError as exc:
        raise ConflictError("A tariff with that effective date already exists; "
                            "tariffs are never edited, so choose a new date.",
                            code="tariff_exists") from exc


@transaction.atomic
def add_meal_tariff(*, item: str, rate: Decimal, effective_from: date,
                    actor=None) -> MealTariff:
    if actor is not None:
        authz.require(actor, perms.TARIFF_MANAGE)
    if item not in meals.PRICED_ITEMS:
        raise BadRequestError(f"Item must be one of {', '.join(meals.PRICED_ITEMS)}.",
                              code="invalid_tariff")
    if rate < 0:
        raise BadRequestError("A rate cannot be negative.", code="invalid_tariff")
    _not_backdated(MealTariff.objects.filter(item=item).exists(), effective_from)
    try:
        with transaction.atomic():
            return MealTariff.objects.create(
                item=item, rate=rate, effective_from=effective_from,
                created_by_user_id=getattr(actor, "user_id", None))
    except IntegrityError as exc:
        raise ConflictError("A tariff with that effective date already exists.",
                            code="tariff_exists") from exc


@transaction.atomic
def create_room(*, actor, number: str, room_type: str, floor: str = "") -> Room:
    authz.require_operator(actor, sm.CARETAKER, perms.ROOM_MANAGE)
    if room_type not in tariffs.ROOM_TYPES:
        raise BadRequestError("Room type must be suite or non_suite.",
                              code="invalid_room_type")
    try:
        with transaction.atomic():
            return Room.objects.create(number=number.strip(), room_type=room_type,
                                       floor=floor)
    except IntegrityError as exc:
        raise ConflictError("A room with that number already exists.",
                            code="duplicate_room") from exc


@transaction.atomic
def set_room_active(*, room_id: int, actor, is_active: bool) -> Room:
    authz.require_operator(actor, sm.CARETAKER, perms.ROOM_MANAGE)
    room = Room.objects.select_for_update().filter(pk=room_id).first()
    if room is None:
        raise NotFoundError("No such room.")
    room.is_active = is_active
    room.save(update_fields=["is_active", "updated_at"])
    return room
