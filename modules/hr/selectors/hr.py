"""HR selectors — all reads go through here."""
from __future__ import annotations

from django.db.models import QuerySet

from modules.hr.models import Department, EmploymentContract


def departments_all() -> QuerySet[Department]:
    return Department.objects.filter(is_active=True).order_by("name")


def department_by_id(department_id: int) -> Department | None:
    return Department.objects.filter(pk=department_id, is_active=True).first()


def contracts_for_user(user_id: int) -> QuerySet[EmploymentContract]:
    return (
        EmploymentContract.objects
        .filter(user_id=user_id)
        .select_related("department")
        .order_by("-starts_on")
    )


def active_contract_for_user(user_id: int) -> EmploymentContract | None:
    return (
        EmploymentContract.objects
        .filter(user_id=user_id, status="active")
        .select_related("department")
        .first()
    )


def active_contracts_all() -> QuerySet[EmploymentContract]:
    return (
        EmploymentContract.objects
        .filter(status="active")
        .select_related("department")
        .order_by("department__name", "title")
    )
