"""Leave fixtures: a frozen Monday, seeded configuration, real designations, and grants read from the registry."""
from datetime import date, timedelta

import pytest
from freezegun import freeze_time
from rest_framework.test import APIClient

from conftest import make_session
from fusion_auth.client import UserRef as IamRef
from modules.directory import contracts as directory
from modules.leave import registry
from modules.leave.services import calendar, configuration

TODAY = date(2026, 3, 2)

FACULTY_CSE = 101
FACULTY_CSE_2 = 102
HOD_CSE = 110
STAFF_GA = 201
STAFF_RO = 202
DEPUTY_REGISTRAR = 300
REGISTRAR = 301
DIRECTOR = 302
HRADMIN = 400
STUDENT = 900

PEOPLE = {
    FACULTY_CSE: ("faculty", "CSE", ("faculty",)),
    FACULTY_CSE_2: ("faculty", "CSE", ("faculty",)),
    HOD_CSE: ("faculty", "CSE", ("faculty", "HOD (CSE)")),
    STAFF_GA: ("staff", "General Administration", ("staff",)),
    STAFF_RO: ("staff", "Registrar Office", ("staff",)),
    DEPUTY_REGISTRAR: ("staff", "Establishment", ("staff", "Deputy Registrar")),
    REGISTRAR: ("staff", "Registrar Office", ("staff", "Registrar")),
    DIRECTOR: ("faculty", "Directorate", ("faculty", "Director")),
    HRADMIN: ("staff", "Establishment", ("staff", "hradmin")),
    STUDENT: ("student", "CSE", ("student",)),
}


IAM_USERS = {uid: IamRef(user_id=uid, username=f"u{uid}", display_name=f"Person {uid}",
                         kind=kind, department=dept, email=f"u{uid}@iiitdmj.test")
             for uid, (kind, dept, _) in PEOPLE.items()}


def permissions_for(roles) -> frozenset[str]:
    return frozenset(c for r in roles for c in registry.ROLE_GRANTS.get(r, []))


@pytest.fixture(autouse=True)
def _frozen():
    with freeze_time("2026-03-02 10:00:00+05:30"):
        yield


@pytest.fixture
def people(db, stub_iam):
    """Projected the way production does it: asked of the (fake) IAM by the directory."""
    stub_iam(users=IAM_USERS)
    assert len(directory.get_users(list(PEOPLE))) == len(PEOPLE)
    return PEOPLE


@pytest.fixture
def actor():
    """A principal for any person above, acting as `as_role` (default: their highest office)."""
    from conftest import make_principal

    def _make(uid, as_role=None, roles=None):
        kind, _, held = PEOPLE[uid]
        held = tuple(roles or held)
        perms = permissions_for(held)
        return make_principal(user_id=uid, kind=kind, roles=held,
                              active_role=as_role or held[-1], permissions=perms,
                              modules=("leave",) if perms else ())
    return _make


@pytest.fixture
def configured(people, actor):
    configuration.seed_policy()
    configuration.seed_hierarchy()
    admin = actor(HRADMIN)
    for year in (2026, 2027):
        cal = calendar.start_draft(actor=admin, year=year)
        calendar.replace_entries(actor=admin, calendar_id=cal.pk, entries=[
            {"date": date(year, 1, 26), "name": "Republic Day", "kind": "closed"},
            {"date": date(year, 3, 4), "name": "Holi", "kind": "closed"},
            {"date": date(year, 3, 10), "name": "Restricted A", "kind": "restricted"},
            {"date": date(year, 8, 15), "name": "Independence Day", "kind": "closed"},
        ])
        calendar.publish(actor=admin, calendar_id=cal.pk)
    calendar.add_vacation(actor=admin, label="Summer 2026", start_date=date(2026, 5, 15),
                          end_date=date(2026, 7, 20), source_reference="AC 2025-26")
    return admin


@pytest.fixture
def client_for(stub_iam):
    """An APIClient signed in as `uid`; the fake IAM also answers holder lookups."""

    def _make(uid, as_role=None, roles=None):
        kind, _, held = PEOPLE[uid]
        held = tuple(roles or held)
        perms = permissions_for(held)
        fake = stub_iam(make_session(user_id=uid, kind=kind, roles=held,
                                     active_role=as_role or held[-1], permissions=perms,
                                     modules=("leave",) if perms else ()), users=IAM_USERS)
        fake.holders = {r: [IamRef(user_id=u, username=f"u{u}", display_name=f"Person {u}",
                                   kind=k, email=f"u{u}@iiitdmj.test", department=d)]
                        for u, (k, d, rs) in PEOPLE.items() for r in rs
                        if r not in ("faculty", "staff", "student")}
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION="Token abc")
        return c
    return _make


def apply_payload(category="CL", start=None, end=None, **extra):
    start = start or TODAY + timedelta(days=7)
    return {"category": category, "start_date": str(start), "end_date": str(end or start),
            "purpose": "Family function", **extra}
