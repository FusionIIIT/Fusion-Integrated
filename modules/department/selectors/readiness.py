"""What the module needs before it works, and which department roles are vacant or ending (Q1)."""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from modules.department.domain.roles import DEPT_ADMIN, HOD, HOD_DESIGNATIONS
from modules.department.models import Department, RoleTenure

ENDING_WITHIN = timedelta(days=30)
LABELS = {HOD: "HOD", DEPT_ADMIN: "Dept_Admin"}


def unmet_prerequisites() -> list[str]:
    if not Department.objects.exists():
        return ["No departments exist yet. Run `python manage.py seed_departments` to create them."]
    return []


def _vacant(dept: Department, role: str) -> dict:
    if role == HOD and dept.code not in set(HOD_DESIGNATIONS.values()):
        hint = f"The ERP has no HOD designation for {dept.code} yet (blueprint Q4)."
    else:
        hint = "Record a tenure on the HOD & Dept_Admin page."
    message = f"{dept.code} has no {LABELS[role]} in effect. {hint}"
    return {"department": dept.code, "role": role, "problem": "vacant", "message": message}


def _ending(dept: Department, role: str, ends) -> dict:
    message = (
        f"The {dept.code} {LABELS[role]} tenure ends on {timezone.localtime(ends):%Y-%m-%d} and no "
        "successor is recorded. Record the next tenure from that moment."
    )
    return {"department": dept.code, "role": role, "problem": "ending", "message": message}


def role_warnings(departments=None, *, now=None) -> list[dict]:
    """BR-DEPT-022: each role with nobody in effect, or ending within 30 days with no successor."""
    now = now or timezone.now()
    depts = list(departments if departments is not None else Department.objects.all())
    tenures = list(RoleTenure.objects.filter(department__in=depts, valid_to__gt=now))
    out = []
    for dept in depts:
        for role in (HOD, DEPT_ADMIN):
            mine = [t for t in tenures if t.department_id == dept.pk and t.role == role]
            current = next((t for t in mine if t.valid_from <= now < t.valid_to), None)
            if current is None:
                out.append(_vacant(dept, role))
            elif current.valid_to - now <= ENDING_WITHIN and not any(
                t.valid_from == current.valid_to for t in mine
            ):
                out.append(_ending(dept, role, current.valid_to))
    return out
