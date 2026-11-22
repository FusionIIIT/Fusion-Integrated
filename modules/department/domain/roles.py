"""Who is acting, and for which department."""

from __future__ import annotations

from dataclasses import dataclass

STUDENT = "student"
FACULTY = "faculty"
HOD = "hod"
DEPT_ADMIN = "dept_admin"
CENTRAL = "central"
SYSTEM = "system"

DEPARTMENT_CODES = ("CSE", "ECE", "ME", "Design", "NS", "SM", "LA")

# Spelled exactly as globals_designation; the designation names its department.
HOD_DESIGNATIONS = {
    "HOD (CSE)": "CSE",
    "HOD (Design)": "Design",
    "HOD (ECE)": "ECE",
    "HOD (Liberal Arts)": "LA",
    "HOD (ME)": "ME",
    "HOD (NS)": "NS",
}

DEPT_ADMIN_DESIGNATIONS = {
    "deptadmin_cse": "CSE",
    "deptadmin_design": "Design",
    "deptadmin_ece": "ECE",
    "deptadmin_liberalarts": "LA",
    "deptadmin_me": "ME",
    "deptadmin_ns": "NS",
    "deptadmin_sm": "SM",
}

# Q3: the "equivalent central authority" of BR-DEPT-021.
CENTRAL_DESIGNATIONS = frozenset({"acadadmin"})

# The ERP spells a department differently in a faculty record and in a discipline.
_ALIASES = {
    "CSE": "CSE",
    "ECE": "ECE",
    "ME": "ME",
    "Design": "Design",
    "Des.": "Design",
    "NS": "NS",
    "Natural Science": "NS",
    "Natural Sciences": "NS",
    "SM": "SM",
    "Smart Manufacturing": "SM",
    "LA": "LA",
    "Liberal Arts": "LA",
}


def normalise_department(raw: str | None) -> str | None:
    if not raw:
        return None
    return _ALIASES.get(raw.strip())


def role_of(active_role: str | None, kind: str | None = None) -> str | None:
    """An office designation decides first, else the basic kind: a student acts as ug_student."""
    if active_role in HOD_DESIGNATIONS:
        return HOD
    if active_role in DEPT_ADMIN_DESIGNATIONS:
        return DEPT_ADMIN
    if active_role in CENTRAL_DESIGNATIONS:
        return CENTRAL
    if active_role is None:
        return None
    if kind == STUDENT or active_role == STUDENT:
        return STUDENT
    if kind == FACULTY or active_role == FACULTY:
        return FACULTY
    return None


def office_department(active_role: str | None) -> str | None:
    """The department an HOD or Dept_Admin designation is for."""
    if active_role in HOD_DESIGNATIONS:
        return HOD_DESIGNATIONS[active_role]
    return DEPT_ADMIN_DESIGNATIONS.get(active_role or "")


@dataclass(frozen=True)
class ActorContext:
    user_id: int | None
    role: str | None
    department: str | None
    programme: str = ""
    batch_year: int | None = None

    @property
    def is_office(self) -> bool:
        return self.role in (HOD, DEPT_ADMIN) and self.department is not None
