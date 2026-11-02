"""Hostel master and role binding services (CFR-HM-001, 002, BR-HM-001, 003, 004)."""

from __future__ import annotations

from datetime import date

from django.db import transaction

from modules.hostel.domain.constants import RoleBindingType
from modules.hostel.domain.errors import ValidationError
from modules.hostel.models import Hostel, HostelRoleBinding


@transaction.atomic
def create_hostel(
    name: str,
    code: str,
    capacity: int,
    gender: str,
    description: str = "",
    creator_user_id: int | None = None,
) -> Hostel:
    """CFR-HM-001, HM-UC-001: Super Admin creates hostel record."""
    if not name or not name.strip():
        raise ValidationError("Hostel name is required")
    if not code or not code.strip():
        raise ValidationError("Hostel code is required")
    if capacity < 0:
        raise ValidationError("Hostel capacity cannot be negative")

    code_clean = code.strip().upper()
    if Hostel.objects.filter(code=code_clean).exists():
        raise ValidationError(f"Hostel with code '{code_clean}' already exists")

    return Hostel.objects.create(
        name=name.strip(),
        code=code_clean,
        capacity=capacity,
        gender=gender,
        description=description.strip(),
        created_by_user_id=creator_user_id,
        is_active=True,
    )


@transaction.atomic
def set_hostel_active_status(
    hostel_id: int, is_active: bool, actor_user_id: int | None = None
) -> Hostel:
    """CFR-HM-001, HM-UC-002: Activate or deactivate hostel record."""
    hostel = Hostel.objects.get(id=hostel_id)
    hostel.is_active = is_active
    hostel.save(update_fields=["is_active", "updated_at"])
    return hostel


@transaction.atomic
def assign_role_binding(
    hostel_id: int,
    user_id: int,
    role: str | RoleBindingType,
    start_date: date | None = None,
    end_date: date | None = None,
    assigner_user_id: int | None = None,
) -> HostelRoleBinding:
    """CFR-HM-002, HM-UC-003, 004, BR-HM-001, 004: Bind Warden or Caretaker to hostel."""
    hostel = Hostel.objects.get(id=hostel_id)

    if start_date and end_date and start_date > end_date:
        raise ValidationError("Start date cannot be after end date")

    # Deactivate existing active binding for the exact same user, hostel and role if any
    HostelRoleBinding.objects.filter(
        hostel=hostel, user_id=user_id, role=str(role), is_active=True
    ).update(is_active=False)

    return HostelRoleBinding.objects.create(
        hostel=hostel,
        user_id=user_id,
        role=str(role),
        start_date=start_date,
        end_date=end_date,
        is_active=True,
        assigned_by_user_id=assigner_user_id,
    )


@transaction.atomic
def deactivate_role_binding(binding_id: int) -> HostelRoleBinding:
    """CFR-HM-002: Deactivate an existing role binding."""
    binding = HostelRoleBinding.objects.get(id=binding_id)
    binding.is_active = False
    binding.save(update_fields=["is_active", "updated_at"])
    return binding
