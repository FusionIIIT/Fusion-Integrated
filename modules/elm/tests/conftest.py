"""ELM fixtures: a published policy and calendar, and principals per role."""
from datetime import date, timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from fusion_auth.client import UserRef
from modules.elm import registry
from modules.elm.domain.policy import DEFAULT_PARAMS
from modules.elm.models import CalendarEntry, CalendarVersion, PolicyVersion
from modules.elm.models.config import PUBLISHED

EMPLOYEE = tuple(registry._EMPLOYEE)
UNIT_HEAD = tuple(registry._UNIT_HEAD)
ESTT = tuple(registry._ESTABLISHMENT)
SANCTION = tuple(registry._SANCTIONING)
ADMIN = tuple(registry._ADMIN)

FAC, FAC2, STF, HOD, DR, REG, DIR, ADM = 101, 102, 201, 301, 401, 501, 601, 701


def monday(weeks_ahead: int = 2) -> date:
    today = timezone.localdate()
    return today + timedelta(days=(7 - today.weekday()) + 7 * (weeks_ahead - 1))


def people() -> dict:
    def u(uid, kind, dept, name):
        return UserRef(user_id=uid, username=f"u{uid}", display_name=name, kind=kind,
                       department=dept)
    return {
        FAC: u(FAC, "faculty", "CSE", "Faculty One"),
        FAC2: u(FAC2, "faculty", "CSE", "Faculty Two"),
        STF: u(STF, "staff", "CSE", "Staff One"),
        HOD: u(HOD, "faculty", "CSE", "Head CSE"),
        DR: u(DR, "staff", "Establishment", "Deputy Registrar"),
        REG: u(REG, "staff", "Registrar Office", "Registrar"),
        DIR: u(DIR, "faculty", "Directorate", "Director"),
        ADM: u(ADM, "staff", "Establishment", "Leave Admin"),
        9001: u(9001, "student", "CSE", "A Student"),
    }


@pytest.fixture
def policy(db):
    return PolicyVersion.objects.create(
        name="test", params=DEFAULT_PARAMS, hierarchy=registry.DEFAULT_HIERARCHY,
        effective_from=date(2000, 1, 1), status=PUBLISHED, published_at=timezone.now())


@pytest.fixture
def calendar(db):
    cv = CalendarVersion.objects.create(name="cal", effective_from=date(2000, 1, 1),
                                        status=PUBLISHED, published_at=timezone.now())
    m = monday(3)
    CalendarEntry.objects.create(version=cv, kind="restricted_holiday", name="RH",
                                 start_date=m + timedelta(days=2),
                                 end_date=m + timedelta(days=2))
    CalendarEntry.objects.create(version=cv, kind="closed_holiday", name="Holiday",
                                 start_date=m + timedelta(days=1),
                                 end_date=m + timedelta(days=1))
    CalendarEntry.objects.create(version=cv, kind="vacation", name="Summer",
                                 start_date=monday(5), end_date=monday(5) + timedelta(days=40))
    return cv


@pytest.fixture
def as_user(stub_iam):
    def _as(uid, perms, *, kind="faculty", roles=None, active_role=None, modules=("elm",)):
        roles = roles or (kind,)
        stub_iam(make_session(user_id=uid, kind=kind, permissions=perms, modules=modules,
                              roles=roles, active_role=active_role or roles[0]),
                 users=people())
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION="Token abc")
        return c
    return _as


def leave(category="CL", start=None, days=1, **kw):
    start = start or monday(2)
    body = {"category": category, "start_date": start.isoformat(),
            "end_date": (start + timedelta(days=days - 1)).isoformat(),
            "purpose": "family function"}
    body.update(kw)
    return body
