"""Fixtures for gymkhana tests: a small institute, and a client acting as one person."""
from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from fusion_auth.client import UserRef
from modules.gymkhana import registry
from modules.gymkhana.domain import state_machine as sm
from modules.gymkhana.models import Club, LeadershipAssignment, Membership
from modules.gymkhana.services.venues import seed_venue_list

STUDENT = tuple(registry.ROLE_GRANTS["student"])
STUDENT_ADMIN = tuple(registry.ROLE_GRANTS["Student Admin"])
FACULTY = tuple(registry.ROLE_GRANTS["faculty"])
MODULES = ("gymkhana",)

ADMIN = 9001
COORD = 1001
CO_COORD = 1002
MEMBER = 1003
PLAIN = 1004
OTHER_COORD = 1005
OTHER_CO = 1006
COUNCILLOR = 2001
OTHER_FACULTY = 2002

DRIVE = "https://drive.google.com/file/d/1AbCdEfGhIjKlMnOp/view"


def people() -> dict[int, UserRef]:
    def stu(uid, batch=2023, disc="CSE"):
        return UserRef(user_id=uid, username=f"stu{uid}", display_name=f"Student {uid}",
                       kind="student", discipline=disc, batch_year=batch,
                       email=f"stu{uid}@example.invalid")
    rows = {uid: stu(uid) for uid in (COORD, CO_COORD, MEMBER, PLAIN, OTHER_COORD,
                                      OTHER_CO)}
    rows[1010] = stu(1010, batch=2024, disc="ECE")
    rows[1011] = stu(1011, batch=None, disc="")
    for uid in (COUNCILLOR, OTHER_FACULTY):
        rows[uid] = UserRef(user_id=uid, username=f"fac{uid}", display_name=f"Faculty {uid}",
                            kind="faculty", email=f"fac{uid}@example.invalid")
    rows[ADMIN] = UserRef(user_id=ADMIN, username="stf9001", display_name="Admin",
                          kind="staff")
    return rows


class Actors:
    def __init__(self, stub_iam):
        self.stub_iam = stub_iam
        self.users = people()

    def client(self, uid, permissions, *, kind="student", modules=MODULES,
               roles=("student",), active_role="student"):
        self.fake = self.stub_iam(
            make_session(user_id=uid, kind=kind, permissions=permissions, modules=modules,
                         roles=roles, active_role=active_role),
            users=self.users)
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION=f"Token t{uid}")
        return c

    def student(self, uid):
        return self.client(uid, STUDENT)

    def admin(self):
        return self.client(ADMIN, STUDENT_ADMIN, kind="staff",
                           roles=("staff", "Student Admin"), active_role="Student Admin")

    def faculty(self, uid=COUNCILLOR):
        return self.client(uid, FACULTY, kind="faculty", roles=("faculty",),
                           active_role="faculty")


@pytest.fixture
def actors(stub_iam):
    return Actors(stub_iam)


def make_club(name="Robotics", *, status=sm.CONFIRMED, coord=COORD, co=CO_COORD,
              councillor=COUNCILLOR, category="technical"):
    now = timezone.now()
    club = Club.objects.create(
        name=name, category=category, description="d", status=status,
        faculty_councillor_user_id=councillor, created_by_user_id=ADMIN,
        approved_by_user_id=ADMIN if status == sm.CONFIRMED else None,
        approved_at=now if status == sm.CONFIRMED else None)
    for uid, role in ((coord, "coordinator"), (co, "co_coordinator")):
        LeadershipAssignment.objects.create(club=club, user_id=uid, role=role,
                                            valid_from=now, assigned_by_user_id=ADMIN)
    return club


def join(club, uid, status=sm.CONFIRMED):
    return Membership.objects.create(club=club, user_id=uid, description="x",
                                     status=status)


@pytest.fixture
def club(db):
    return make_club()


@pytest.fixture
def other_club(db):
    return make_club("Dramatics", coord=OTHER_COORD, co=OTHER_CO,
                     councillor=OTHER_FACULTY, category="cultural")


@pytest.fixture
def venues(db):
    return seed_venue_list(names=["LHTC 101", "Open Air Theatre"],
                           effective_from=timezone.now() - timedelta(days=1))


def tomorrow() -> str:
    return (timezone.localdate() + timedelta(days=1)).isoformat()


def session_body(club_id, *, start="10:00", end="11:00", venue="LHTC 101", day=None):
    return {"club_id": club_id, "venue": venue, "date": day or tomorrow(),
            "start_time": start, "end_time": end, "description": "Weekly build"}


def event_body(club_id, **kw):
    return {**session_body(club_id, **kw), "event_name": "RoboWars", "poster_url": DRIVE}


def poll_body(club_id, **kw):
    body = {"club_id": club_id, "title": "Next workshop", "description": "Pick one",
            "expires_on": (timezone.localdate() + timedelta(days=3)).isoformat(),
            "choices": ["Drones", "ROS"],
            "targets": [{"batch_year": 2023, "discipline": "CSE"}]}
    body.update(kw)
    return body

