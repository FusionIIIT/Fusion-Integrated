"""What Leave still needs before it can work, each item a sentence an operator can act on."""
from __future__ import annotations

from django.db.utils import DatabaseError
from django.utils import timezone

from modules.directory import contracts as directory
from modules.leave.models import HierarchyRevision, HolidayCalendar, PolicyRevision
from modules.leave.services import configuration


def unmet() -> list[str]:
    try:
        return _unmet()
    except DatabaseError as exc:
        return [f"The leave tables are not readable ({exc.__class__.__name__}); run migrate."]


def _unmet() -> list[str]:
    year = timezone.localdate().year
    problems = []
    if not PolicyRevision.objects.exists():
        problems.append("No leave policy is configured: run `manage.py leave_seed`.")
    if not HierarchyRevision.objects.exists():
        problems.append("No approval hierarchy is configured: run `manage.py leave_seed`, then "
                        "review the Unit Heads and routes.")
    if not HolidayCalendar.objects.filter(year=year, status=HolidayCalendar.PUBLISHED).exists():
        problems.append(f"No holiday calendar is published for {year}: publish one on the "
                        f"Holiday Calendar screen.")
    return problems


def warnings() -> list[str]:
    """Not blocking, but somebody will be refused: employees whose unit has no Unit Head."""
    h = configuration.current_hierarchy(required=False)
    mapped = set(h.units) if h else set()
    unmapped: dict[str, int] = {}
    for e in directory.get_employees():
        if e.department not in mapped:
            key = e.department or "(no department on record)"
            unmapped[key] = unmapped.get(key, 0) + 1
    return [f"{n} employee(s) in {dept} have no Unit Head configured and cannot apply."
            for dept, n in sorted(unmapped.items())]
