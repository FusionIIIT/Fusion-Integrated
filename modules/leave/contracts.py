"""ELM's public read surface and explicit external provider boundaries."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from importlib import import_module

from django.conf import settings

from fusion_auth.client import IamUnavailable
from modules.directory import contracts as directory


class ExternalDependencyUnavailable(RuntimeError):
    """A required provider is not configured or could not be reached."""


@dataclass(frozen=True)
class EmployeeDTO:
    user_id: int
    display_name: str
    email: str
    kind: str
    organizational_unit: str


def get_employees(user_ids: Sequence[int]) -> dict[int, EmployeeDTO]:
    """Read employee identities through the shared directory contract."""
    rows = directory.get_users(user_ids)
    return {
        user_id: EmployeeDTO(
            user_id=row.user_id, display_name=row.display_name, email=row.email,
            kind=row.kind, organizational_unit=row.department,
        )
        for user_id, row in rows.items() if row.kind in {"faculty", "staff"}
    }


def _active_employees() -> list[EmployeeDTO]:
    """Batch source used only by ELM's scheduled year-end operation."""
    return [
        EmployeeDTO(
            user_id=row.user_id, display_name=row.display_name, email=row.email,
            kind=row.kind, organizational_unit=row.department,
        )
        for row in directory.get_employees()
    ]


def _provider(setting_name: str):
    path = getattr(settings, setting_name, "")
    if not path:
        raise ExternalDependencyUnavailable(f"{setting_name} is not configured.")
    module_path, _, attr = path.rpartition(".")
    if not module_path:
        raise ExternalDependencyUnavailable(f"{setting_name} must be a dotted callable path.")
    return getattr(import_module(module_path), attr)


def academic_vacation_periods(start_date, end_date):
    """Delegate vacation data to the configured Academic Calendar adapter."""
    return _provider("ELM_ACADEMIC_CALENDAR_PROVIDER")(start_date, end_date)


def synchronize_attendance(*, user_id: int, start_date, end_date):
    """Delegate attendance synchronization without fabricating an ERP result."""
    return _provider("ELM_ATTENDANCE_PROVIDER")(
        user_id=user_id, start_date=start_date, end_date=end_date)


__all__ = [
    "EmployeeDTO",
    "ExternalDependencyUnavailable",
    "IamUnavailable",
    "academic_vacation_periods",
    "get_employees",
    "synchronize_attendance",
]
