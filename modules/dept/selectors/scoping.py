import re

from django.db.models import Q

from core.api.exceptions import NotFoundError
from modules.dept.models import Department


def department_scope(actor, department_code=None, roles=()):
    code = (department_code or "").strip().upper()
    if actor.active_role in {"HOD", "Dept_Admin"}:
        rows = [
            a
            for a in actor.department_assignments
            if a.get("role") == actor.active_role
            and (not code or a.get("department_code", "").upper() == code)
        ]
        if len(rows) != 1 or (roles and actor.active_role not in roles):
            raise NotFoundError("Department was not found in your active role.")
        claim = rows[0]
        department, _ = Department.objects.get_or_create(
            code=claim["department_code"],
            defaults={"name": claim.get("department_name") or claim["department_code"]},
        )
        return department
    if actor.kind not in {"student", "faculty", "staff"}:
        raise NotFoundError("Department was not found.")
    if not actor.department:
        raise NotFoundError("Department was not found.")
    department = Department.objects.filter(
        Q(code__iexact=actor.department) | Q(name__iexact=actor.department)
    ).first()
    # Older IAM sessions provide a canonical department code in `user.department`
    # but predate the richer department_contexts claim. Bootstrap that code into
    # the local display/scope table; never turn an arbitrary display label into
    # an authorization key.
    if department is None and re.fullmatch(r"[A-Z0-9_-]{2,48}", actor.department):
        department, _ = Department.objects.get_or_create(
            code=actor.department,
            defaults={"name": actor.department},
        )
    if department is None or (code and department.code != code):
        raise NotFoundError("Department was not found.")
    return department
