from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from modules.leave.models import Holiday, LeaveBalance, LeavePolicy, LeaveRequest, OrgUnit
from modules.leave.services import authz

P_SAVE_POLICY = "leave.policy.manage"
P_SAVE_UNIT = "leave.policy.manage"
P_ADD_HOLIDAY = "leave.calendar.manage"
P_RECORD_OFFLINE_LEAVE = "leave.offline.record"


@transaction.atomic
def save_policy(
    *, actor, category, annual_entitlement, carries_forward, applies_to, is_active=True
) -> LeavePolicy:
    """EL-UC-014, BR-EL-029: Save or update a leave policy."""
    authz.require(actor, P_SAVE_POLICY)
    policy, created = LeavePolicy.objects.update_or_create(
        category=category,
        defaults={
            "annual_entitlement": annual_entitlement,
            "carries_forward": carries_forward,
            applies_to: applies_to,
            "is_active": is_active,
        },
    )
    return policy


@transaction.atomic
def save_unit(*, actor, name, unit_head_user_id) -> OrgUnit:
    """EL-UC-014, BR-EL-029: Save or update an organizational unit."""
    authz.require(actor, P_SAVE_UNIT)
    unit, created = OrgUnit.objects.update_or_create(
        name=name, defaults={"unit_head_user_id": unit_head_user_id}
    )
    return unit


@transaction.atomic
def add_holiday(*, actor, date, name, is_restricted=False, is_published=True) -> None:
    """EL-UC-015, BR-EL-030: Add a holiday to the calendar."""
    authz.require(actor, P_ADD_HOLIDAY)
    Holiday.objects.create(
        date=date,
        name=name,
        is_restricted=is_restricted,
        is_published=is_published,
    )


@transaction.atomic
def record_offline_leave(*, actor, user_id, category, start_date, end_date, days, note="") -> None:
    """EL-UC-016, BR-EL-029: Record offline-sanctioned leave."""
    authz.require(actor, P_RECORD_OFFLINE_LEAVE)
    LeaveRequest.objects.create(
        user_id=user_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        days=days,
        purpose=note,
        is_offline=True,
        status="approved",
    )
    LeaveBalance.objects.filter(user_id=user_id, category=category).update(
        used=days,
        updated_at=timezone.now(),
    )


def ensure_balances(*, user_id, year) -> list[LeaveBalance]:
    """BR-EL-037: Ensure leave balances are up-to-date."""
    from modules.leave.domain.categories import ENTITLEMENT

    balances = []
    for category, entitlement in ENTITLEMENT.items():
        balance, created = LeaveBalance.objects.get_or_create(
            user_id=user_id, year=year, category=category, defaults={"entitled": entitlement}
        )
        balances.append(balance)
    return balances
