"""Shared ELM fixtures: the desks of the routing hierarchy, a published
calendar, and a client factory that logs in as any of them."""
from __future__ import annotations

from datetime import date

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory.models import UserRef
from modules.leave.models import (
    AuthorityAssignment,
    Holiday,
    HolidayCalendar,
    LeavePolicy,
    OrganizationalUnit,
    SlaThreshold,
)

APPLICANT = 9100
UNIT_HEAD = 9001
ESTABLISHMENT = 9002
DEAN = 9003
REGISTRAR = 9004
DIRECTOR = 9005
SUBSTITUTE = 9101
OTHER = 9199
UNPLACED = 9102          # staff whose department maps to no org unit

SELF = ("leave.request.view_self", "leave.request.create",
        "leave.request.delete", "leave.substitute.respond")
UH = (*SELF, "leave.request.view", "leave.request.approve")
EST = (*SELF, "leave.request.view", "leave.request.route")
AUTH = (*SELF, "leave.request.view", "leave.request.sanction")
ADMIN = ("leave.request.view", "leave.balance.view", "leave.balance.update",
         "leave.type.manage", "leave.calendar.manage",
         "leave.record.manage", "leave.sla.manage")


def _user(uid: int, name: str, kind: str, department: str = "") -> None:
    UserRef.objects.update_or_create(
        user_id=uid,
        defaults={"username": f"u{uid}", "display_name": name, "kind": kind,
                  "department": department})


@pytest.fixture
def desks():
    """The eight people a routing hierarchy needs, plus config."""
    _user(APPLICANT, "Asha Verma", "staff", "CSE")
    _user(UNIT_HEAD, "Head of CSE", "faculty", "CSE")
    _user(ESTABLISHMENT, "Establishment Clerk", "staff", "")
    _user(DEAN, "Dean Academic", "faculty", "")
    _user(REGISTRAR, "Registrar Office", "staff", "")
    _user(DIRECTOR, "The Director", "faculty", "")
    _user(SUBSTITUTE, "Suresh Patil", "staff", "CSE")
    _user(OTHER, "Other Person", "staff", "ECE")
    _user(UNPLACED, "No Unit Here", "staff", "NOWHERE")

    LeavePolicy.objects.get_or_create(id=1)
    cse = OrganizationalUnit.objects.create(
        code="CSE", name="Computer Science & Engineering",
        head_user_id=UNIT_HEAD)
    OrganizationalUnit.objects.create(code="ECE", name="ECE",
                                      head_user_id=OTHER)
    for role, uid in [("establishment", ESTABLISHMENT), ("dean", DEAN),
                      ("registrar", REGISTRAR), ("director", DIRECTOR)]:
        AuthorityAssignment.objects.create(role_code=role, user_id=uid)

    calendar = HolidayCalendar.objects.create(
        title="2026", academic_year="2026-27",
        status=HolidayCalendar.PUBLISHED, published_at=timezone.now(),
        published_by_user_id=REGISTRAR)
    Holiday.objects.create(calendar=calendar, date=date(2026, 11, 8),
                           name="Diwali (Sunday)", kind="restricted")
    Holiday.objects.create(calendar=calendar, date=date(2026, 10, 21),
                           name="Mid Autumn", kind="restricted")
    Holiday.objects.create(calendar=calendar, date=date(2026, 8, 15),
                           name="Independence Day", kind="closed")

    for task_class in ("substitute_response", "unit_head_review",
                       "establishment_routing", "final_sanction",
                       "director_sanction", "resumption_review"):
        SlaThreshold.objects.get_or_create(
            task_class=task_class,
            defaults={"reminder_hours": 24, "escalation_hours": 48,
                      "escalation_user_id": DEAN})
    return {"calendar": calendar, "cse": cse}


@pytest.fixture
def client(stub_iam):
    """client(user_id, permissions=...) → an authenticated APIClient.

    Each caller gets its own token mapping to its own session, so several
    desks can be logged in at once — a single shared session would make
    every earlier client silently act as whoever logged in last."""
    fake = stub_iam()
    tokens: dict = {}

    def _resolve(*, auth_token=None, cookies=None):
        return tokens.get(auth_token)

    fake.resolve_session = _resolve

    def _make(user_id: int, kind: str = "staff", permissions=(),
              modules=("leave",)):
        token = f"tok-{user_id}-{len(tokens)}"
        tokens[token] = make_session(
            user_id=user_id, kind=kind,
            permissions=tuple(permissions),
            modules=tuple(modules),
            roles=(kind,), active_role=kind)
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        return c
    return _make
