from datetime import timedelta
from types import SimpleNamespace

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.lms.models import CoursePolicyVersion, CourseWorkspace
from modules.lms.registry import ROLE_GRANTS

KEY = "cof_" + "a" * 64
OTHER_KEY = "cof_" + "b" * 64
ACTORS = {
    "faculty": (1, "FACULTY"),
    "student": (2, "STUDENT"),
    "lms_ta": (3, "TA"),
    "lms_observer": (4, "OBSERVER"),
}


@pytest.fixture
def world(stub_iam):
    fake = stub_iam()
    workspace = CourseWorkspace.objects.create(external_offering_key=KEY)
    other = CourseWorkspace.objects.create(external_offering_key=OTHER_KEY)
    CoursePolicyVersion.objects.create(
        workspace=workspace, version=1, effective_from=timezone.now()
    )
    fake.course_offerings = [
        {
            "offering_key": KEY,
            "course_code": "SYN101",
            "course_name": "Synthetic Course",
            "working_year": 2026,
            "session": "AUTUMN",
            "instructor_user_ids": [1],
            "ta_user_ids": [3],
        },
        {"offering_key": OTHER_KEY, "course_code": "SYN102", "course_name": "Other Course"},
    ]
    fake.course_associations = [
        {
            "user_id": uid,
            "offering_key": KEY,
            "course_role": role,
            "source_origin": "fusion_registration" if role == "STUDENT" else "synthetic_fixture",
        }
        for uid, role in ACTORS.values()
    ]

    def actor(role="faculty", *, uid=None, permissions=None, modules=("lms",), roles=None):
        session = make_session(
            user_id=uid or ACTORS[role][0],
            kind="faculty" if role == "faculty" else "student",
            permissions=ROLE_GRANTS[role] if permissions is None else permissions,
            modules=modules,
            active_role=role,
            roles=roles or (role,),
        )
        stub_iam(session)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token fixture-session")
        return client

    return SimpleNamespace(
        workspace=workspace,
        other=other,
        fake=fake,
        actor=actor,
        due=timezone.now() + timedelta(days=1),
    )


def draft(world, *, submission_type="TEXT", **kwargs):
    data = {
        "instructions": "Implement the exercise",
        "due_at": world.due.isoformat(),
        "submission_type": submission_type,
        "points_possible": "20.00",
        **kwargs,
    }
    response = world.actor().post(
        f"/api/v1/lms/courses/{world.workspace.pk}/assignments/", data, format="json"
    )
    assert response.status_code == 201, response.content
    return response.json()


def available(world, **kwargs):
    row = draft(world, **kwargs)
    response = world.actor().post(
        f"/api/v1/lms/assignments/{row['id']}/publish/", {}, format="json"
    )
    assert response.status_code == 200, response.content
    return response.json()


def submit(world, assignment, **kwargs):
    response = world.actor("student").post(
        f"/api/v1/lms/assignments/{assignment['id']}/submissions/",
        {"kind": "TEXT", "text": "Student work", **kwargs},
        format="json",
    )
    assert response.status_code == 201, response.content
    return response.json()
