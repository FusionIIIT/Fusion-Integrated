"""Hostel master and role binding services (3.0, CFR-HM-001, CFR-HM-002, BR-HM-001, BR-HM-003, BR-HM-004)."""

from datetime import date
from django.db import transaction
from ..domain.errors import HostelDomainError
from ..models import Hostel, HostelRoleBinding
from .notification_service import create_notification


@transaction.atomic
def create_hostel(
    name: str,
    code: str,
    gender_policy: str = "coed",
    capacity: int = 0,
    description: str = "",
) -> Hostel:
    if Hostel.objects.filter(code__iexact=code).exists():
        raise HostelDomainError(f"Hostel with code '{code}' already exists.", code="duplicate_code")
    if Hostel.objects.filter(name__iexact=name).exists():
        raise HostelDomainError(f"Hostel with name '{name}' already exists.", code="duplicate_name")

    return Hostel.objects.create(
        name=name.strip(),
        code=code.strip().upper(),
        gender_policy=gender_policy,
        capacity=capacity,
        description=description.strip(),
        is_active=True,
    )


@transaction.atomic
def update_hostel(
    hostel_id: int,
    name: str | None = None,
    gender_policy: str | None = None,
    capacity: int | None = None,
    description: str | None = None,
) -> Hostel:
    hostel = Hostel.objects.filter(id=hostel_id).first()
    if not hostel:
        raise HostelDomainError(f"Hostel {hostel_id} not found.", code="not_found")

    if name:
        conflict = Hostel.objects.filter(name__iexact=name.strip()).exclude(id=hostel_id).exists()
        if conflict:
            raise HostelDomainError(f"Hostel with name '{name}' already exists.", code="duplicate_name")
        hostel.name = name.strip()
    if gender_policy:
        hostel.gender_policy = gender_policy
    if capacity is not None:
        hostel.capacity = capacity
    if description is not None:
        hostel.description = description.strip()

    hostel.save()
    return hostel


@transaction.atomic
def toggle_hostel_status(hostel_id: int, is_active: bool) -> Hostel:
    hostel = Hostel.objects.filter(id=hostel_id).first()
    if not hostel:
        raise HostelDomainError(f"Hostel {hostel_id} not found.", code="not_found")

    hostel.is_active = is_active
    hostel.save(update_fields=["is_active", "updated_at"])
    return hostel


@transaction.atomic
def create_or_update_role_binding(
    hostel_id: int,
    user_id: int,
    role: str,
    assigned_by_user_id: int,
    is_active: bool = True,
    start_date: date | None = None,
    end_date: date | None = None,
    notes: str = "",
) -> HostelRoleBinding:
    """Super Admin assigns, reassigns, activates, or deactivates Warden/Caretaker binding (BR-HM-001)."""
    hostel = Hostel.objects.filter(id=hostel_id).first()
    if not hostel:
        raise HostelDomainError(f"Hostel {hostel_id} not found.", code="not_found")

    binding, created = HostelRoleBinding.objects.update_or_create(
        hostel=hostel,
        user_id=user_id,
        role=role,
        defaults={
            "is_active": is_active,
            "start_date": start_date,
            "end_date": end_date,
            "assigned_by_user_id": assigned_by_user_id,
            "notes": notes,
        },
    )

    action = "assigned" if created else ("activated" if is_active else "deactivated")
    create_notification(
        recipient_user_id=user_id,
        event_type="role_binding_update",
        title=f"Hostel Role {action.capitalize()}",
        message=f"You have been {action} as {role.capitalize()} for {hostel.name}.",
        reference_id=str(binding.id),
    )

    return binding
