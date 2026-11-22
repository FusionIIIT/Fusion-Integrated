"""A small department world: people as the IAM projects them, tenures, and a client per role."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from fusion_auth.client import UserRef
from modules.department.models import Department, RoleTenure
from modules.department.registry import ROLE_GRANTS
from modules.directory import contracts as directory


@dataclass(frozen=True)
class Person:
    user_id: int
    kind: str
    designation: str
    department: str = ""
    discipline: str = ""
    programme: str = ""
    batch_year: int | None = None


PEOPLE = {
    "student": Person(
        2001, "student", "ug_student", discipline="CSE", programme="B.Tech", batch_year=2024
    ),
    "student2": Person(
        2002, "student", "student", discipline="CSE", programme="B.Tech", batch_year=2023
    ),
    "ece_student": Person(
        2101, "student", "student", discipline="ECE", programme="B.Tech", batch_year=2024
    ),
    "faculty": Person(3001, "faculty", "Assistant Professor", department="CSE"),
    "faculty2": Person(3002, "faculty", "faculty", department="CSE"),
    "ece_faculty": Person(3101, "faculty", "faculty", department="ECE"),
    "hod": Person(3010, "faculty", "HOD (CSE)", department="CSE"),
    "next_hod": Person(3011, "faculty", "HOD (CSE)", department="CSE"),
    "ece_hod": Person(3110, "faculty", "HOD (ECE)", department="ECE"),
    "admin": Person(4010, "staff", "deptadmin_cse", department="CSE"),
    "ece_admin": Person(4110, "staff", "deptadmin_ece", department="ECE"),
    "central": Person(5001, "staff", "acadadmin", department="Academics"),
    "outsider": Person(6001, "staff", "Hostel_admin", department="IWD"),
}


def user_refs() -> dict[int, UserRef]:
    return {
        p.user_id: UserRef(
            user_id=p.user_id,
            username=f"u{p.user_id}",
            display_name=f"Person {p.user_id}",
            kind=p.kind,
            email=f"u{p.user_id}@example.test",
            department=p.department,
            discipline=p.discipline,
            programme=p.programme,
            batch_year=p.batch_year,
        )
        for p in PEOPLE.values()
    }


def session_for(name: str, *, permissions=None, modules=("department",), active_role=None):
    p = PEOPLE[name]
    role = active_role or p.designation
    roles = tuple(dict.fromkeys((p.kind, p.designation)))
    # As the IAM builds /me: the permissions of every role held, not only the acting one.
    held = {c for r in roles for c in ROLE_GRANTS.get(r, [])}
    perms = held if permissions is None else permissions
    return make_session(
        user_id=p.user_id,
        kind=p.kind,
        permissions=perms,
        modules=modules,
        roles=roles,
        active_role=role,
    )


@pytest.fixture
def world(db):
    call_command("seed_departments", stdout=StringIO())
    now = timezone.now()
    cse, ece = Department.objects.get(code="CSE"), Department.objects.get(code="ECE")
    long = timedelta(days=365)
    for dept, name, role in [
        (cse, "hod", "hod"),
        (cse, "admin", "dept_admin"),
        (ece, "ece_hod", "hod"),
        (ece, "ece_admin", "dept_admin"),
    ]:
        RoleTenure.objects.create(
            department=dept,
            role=role,
            user_id=PEOPLE[name].user_id,
            valid_from=now - timedelta(days=1),
            valid_to=now + long,
            assigned_by=PEOPLE["central"].user_id,
            transition_applied_at=now - timedelta(days=1),
        )
    return {"CSE": cse, "ECE": ece}


@pytest.fixture
def act(stub_iam):
    """act("hod") -> an APIClient signed in as that person in that role."""

    def _as(name: str, **kw) -> APIClient:
        users = user_refs()
        stub_iam(session_for(name, **kw), users=users)
        directory.get_users(list(users))
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token abc")
        return client

    return _as


def uid(name: str) -> int:
    return PEOPLE[name].user_id
