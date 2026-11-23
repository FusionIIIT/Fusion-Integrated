"""Helpers shared by the Gymkhana tests."""
import datetime

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory.models import UserRef
from modules.gymkhana.models import Club, Poll, PollChoice, PollTargetGroup
from modules.gymkhana.registry import ROLE_GRANTS

API = "/api/v1/gymkhana"
HEAD, CO_HEAD, STUDENT, OTHER_STUDENT = 101, 102, 103, 104
OTHER_HEAD, OTHER_CO_HEAD = 111, 112
COUNCILLOR, OTHER_FACULTY, ADMIN = 201, 202, 900


def now():
    return datetime.datetime.now(datetime.UTC)


def people():
    for uid in (HEAD, CO_HEAD, STUDENT, OTHER_STUDENT, OTHER_HEAD, OTHER_CO_HEAD, ADMIN):
        UserRef.objects.create(
            user_id=uid, username=f"u{uid}", display_name=f"User {uid}", kind="student",
            email=f"u{uid}@example.invalid", batch_year=2024, discipline="CSE",
        )
    UserRef.objects.filter(user_id=OTHER_STUDENT).update(batch_year=2023, discipline="ECE")
    for uid in (COUNCILLOR, OTHER_FACULTY):
        UserRef.objects.create(
            user_id=uid, username=f"u{uid}", display_name=f"User {uid}", kind="faculty"
        )


def sign_in(stub_iam, user_id, *roles, active=None, modules=("gymkhana",), permissions=None):
    """Signed in with exactly what the registry grants those roles, as the IAM sends it."""
    roles = roles or ("student",)
    if permissions is None:
        permissions = {code for role in roles for code in ROLE_GRANTS.get(role, ())}
    stub_iam(make_session(
        user_id=user_id, kind="faculty" if "faculty" in roles else "student", roles=roles,
        active_role=active or roles[-1], modules=modules, permissions=permissions,
    ))
    client = APIClient(raise_request_exception=False)
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    return client


def make_club(name="Robotics Club", status="confirmed", heads=(HEAD, CO_HEAD),
              councillor=COUNCILLOR):
    return Club.objects.create(
        name=name, category="technical", coordinator_id=heads[0], co_coordinator_id=heads[1],
        faculty_councillor_id=councillor, status=status,
    )


def make_poll(club, *groups, title="Poll", expires_in=datetime.timedelta(days=1)):
    poll = Poll.objects.create(
        club=club, created_by_id=HEAD, title=title, expires_at=now() + expires_in
    )
    for text in ("Yes", "No"):
        PollChoice.objects.create(poll=poll, choice_text=text)
    for batch, branch in groups or (("all", "all"),):
        PollTargetGroup.objects.create(poll=poll, batch=batch, branch=branch)
    return poll


def upload(name="paper.pdf", content=b"%PDF-1.4 paper"):
    return SimpleUploadedFile(name, content)


def slot(club, **changes):
    return {
        "club_id": club.pk, "venue": "Hall 1", "booking_date": "2027-03-01",
        "start_time": "10:00", "end_time": "11:00", "description": "Weekly", **changes,
    }


def new_poll(club, **changes):
    return {
        "club_id": club.pk, "title": "Next workshop", "description": "",
        "expires_at": (now() + datetime.timedelta(days=2)).isoformat(),
        "choices": ["Arduino", "ROS"],
        "target_groups": [{"batch": "2024", "branch": "CSE"}], **changes,
    }
