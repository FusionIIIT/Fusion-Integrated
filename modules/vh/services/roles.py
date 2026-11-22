# Operational role management and record transfer services for VHMS.
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError
from modules.vh.models.booking import Booking
from modules.vh.models.inventory import InventoryReplenishment
from modules.vh.models.roles import OperationalRoleHolder


@transaction.atomic
def reassign_operational_role(
    role_name: str,
    new_user_id: int,
    valid_from: datetime | None,
    valid_to: datetime | None,
    principal,
) -> OperationalRoleHolder:
    # CFR-VH-017, BR-VH-045..050: Reassigns Caretaker or In-Charge role immediately.
    rname = role_name.strip().lower()
    if rname not in {"caretaker", "incharge"}:
        raise BadRequestError("Role name must be 'caretaker' or 'incharge'.")

    # Deactivate existing active role holder immediately (BR-VH-045, BR-VH-046, BR-VH-048)
    now = timezone.now()
    OperationalRoleHolder.objects.filter(role_name=rname, is_active=True).update(
        is_active=False,
        valid_to=now,
    )

    new_holder = OperationalRoleHolder.objects.create(
        role_name=rname,
        user_id=new_user_id,
        valid_from=valid_from or now,
        valid_to=valid_to,
        is_active=True,
    )

    # Transfer pending and ongoing records to new role holder (BR-VH-049, BR-VH-050)
    transfer_pending_and_ongoing_records(rname, new_user_id)
    return new_holder


def transfer_pending_and_ongoing_records(role_name: str, new_user_id: int) -> int:
    # Transfers operational ownership of pending and active records.
    count = 0
    if role_name == "caretaker":
        # Pending reviews and active stays are now under new caretaker operational desk
        count += Booking.objects.filter(
            status__in=["pending", "pending_offline", "approved", "room_allotted", "checked_in"]
        ).count()
    elif role_name == "incharge":
        # Forwarded bookings and pending replenishment requests route to new In-Charge
        count += Booking.objects.filter(status__in=["forwarded", "forwarded_offline"]).count()
        count += InventoryReplenishment.objects.filter(status="pending").count()
    return count
