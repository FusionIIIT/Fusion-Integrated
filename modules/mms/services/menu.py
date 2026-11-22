"""Weekly menu (BR-MMS-014/015/039; UC-008/009)."""

from __future__ import annotations

from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError
from modules.mms.domain import rules
from modules.mms.domain.exceptions import GuardFailed
from modules.mms.models import MenuItem
from modules.mms.selectors import scoping
from modules.mms.services import authz, notifications


def list_items(actor):
    qs = scoping.menu_items_for(actor)
    return qs.order_by("day", "meal")


def upsert_item(actor, day, meal: str, item: str, pk: int | None = None) -> MenuItem:
    """BR-MMS-039: only the Caretaker adds, deletes or modifies menu items."""
    authz.require(actor, "mms.menu.manage")
    try:
        rules.valid_menu_meal(meal)
    except GuardFailed as exc:
        raise ConflictError(exc.message) from exc
    with transaction.atomic():
        if pk is None:
            obj = MenuItem.objects.create(
                day=day, meal=meal, item=item, created_by_user_id=actor.user_id
            )
        else:
            obj = scoping.menu_items_for(actor).filter(pk=pk).select_for_update().first()
            if obj is None:
                raise NotFoundError("No menu item with that id.")
            obj.day = day
            obj.meal = meal
            obj.item = item
            obj.save(update_fields=["day", "meal", "item", "updated_at"])
        notifications.enqueue(
            topic="menu.updated",
            dedupe_key=f"menu.updated:{day}:{meal}",
            subject="Weekly menu updated",
            body=f"The weekly menu for {day} ({meal}) has been updated.",
            recipient_email="mms-broadcast@invalid",
            payload={"audience": "students", "day": str(day), "meal": meal},
        )
    return obj


def delete_item(actor, pk: int) -> None:
    authz.require(actor, "mms.menu.manage")
    with transaction.atomic():
        obj = scoping.menu_items_for(actor).filter(pk=pk).select_for_update().first()
        if obj is None:
            raise NotFoundError("No menu item with that id.")
        day, meal = obj.day, obj.meal
        obj.delete()
        notifications.enqueue(
            topic="menu.updated",
            dedupe_key=f"menu.updated:{day}:{meal}:deleted",
            subject="Weekly menu updated",
            body=f"A menu item for {day} ({meal}) has been removed.",
            recipient_email="mms-broadcast@invalid",
            payload={"audience": "students", "day": str(day), "meal": meal},
        )
