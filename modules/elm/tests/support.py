"""Shared builders for the ELM tests: a small directory and principals to act as."""
from __future__ import annotations

import datetime as dt

from conftest import make_principal
from fusion_auth.client import UserRef

D = dt.date

EMPLOYEE, PEER, STAFF_MEMBER = 1001, 1002, 1003
UNIT_HEAD, OTHER_UNIT_HEAD = 2001, 2002
ESTABLISHMENT, SANCTIONER, DIRECTOR, ADMIN = 3001, 4001, 5001, 6001
STUDENT = 9001


def _person(user_id: int, kind: str = "faculty", department: str = "CSE") -> UserRef:
    return UserRef(user_id=user_id, username=f"u{user_id}", display_name=f"User {user_id}",
                   kind=kind, department=department)


DIRECTORY = {
    EMPLOYEE: _person(EMPLOYEE), PEER: _person(PEER),
    STAFF_MEMBER: _person(STAFF_MEMBER, "staff"),
    UNIT_HEAD: _person(UNIT_HEAD), OTHER_UNIT_HEAD: _person(OTHER_UNIT_HEAD, department="ECE"),
    ESTABLISHMENT: _person(ESTABLISHMENT, "staff", "Estt"),
    SANCTIONER: _person(SANCTIONER, "faculty", "Admin"),
    DIRECTOR: _person(DIRECTOR, "faculty", "Admin"),
    ADMIN: _person(ADMIN, "staff", "Estt"),
    STUDENT: _person(STUDENT, "student"),
}

EMPLOYEE_PERMS = ("elm.leave.apply", "elm.leave.view")
UNIT_HEAD_PERMS = (*EMPLOYEE_PERMS, "elm.leave.review")
ESTABLISHMENT_PERMS = (*EMPLOYEE_PERMS, "elm.leave.route")
SANCTION_PERMS = (*EMPLOYEE_PERMS, "elm.leave.sanction")
DIRECTOR_PERMS = (*EMPLOYEE_PERMS, "elm.leave.self_sanction")
ADMIN_PERMS = (*EMPLOYEE_PERMS, "elm.leave.administer")


def acting(user_id: int, permissions=EMPLOYEE_PERMS, *, kind: str | None = None, modules=("elm",)):
    kind = kind or DIRECTORY[user_id].kind
    return make_principal(user_id=user_id, kind=kind, permissions=permissions, modules=modules)


FIRST_DAY = D(2026, 3, 2)


def request(leave_type="CL", start=FIRST_DAY, end=None, **extra):
    """A valid application body; override whatever a test is about."""
    return {"leave_type": leave_type, "start_date": start, "end_date": end or start,
            "half_day": "NONE", **extra}
