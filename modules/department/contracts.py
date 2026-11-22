"""department's public surface. Plural by signature."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from modules.department.models import Department
from modules.department.selectors.actors import current_holders


@dataclass(frozen=True)
class HeadshipDTO:
    department_code: str
    hod_user_id: int | None


def get_headships(department_codes: Sequence[str]) -> dict[str, HeadshipDTO]:
    """AFR-DEPT-053: the HOD whose tenure is in effect now, per department."""
    depts = list(Department.objects.filter(code__in=set(department_codes)))
    holders = current_holders([d.pk for d in depts], "hod")
    return {d.code: HeadshipDTO(d.code, holders.get(d.pk)) for d in depts}
