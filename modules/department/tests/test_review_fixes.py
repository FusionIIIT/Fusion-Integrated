from concurrent.futures import ThreadPoolExecutor
from datetime import time
from threading import Barrier

import pytest
from django.db import IntegrityError, connections, transaction
from django.urls import reverse
from rest_framework.test import APIClient

from conftest import make_principal, make_session
from core.api.csrf import token_for
from core.api.exceptions import ConflictError
from core.api.throttling import PrincipalScopedThrottle
from fusion_auth.client import UserRef
from modules.department.administration import upload_timetable
from modules.department.api.urls import urlpatterns
from modules.department.models import Feedback, TimetableSlot
from modules.department.permissions import SUBMIT_FEEDBACK, UPDATE_TIMETABLE, VIEW_ANNOUNCEMENT
from modules.department.registry import ROLE_GRANTS

BASE_SLOT = {
    "department": "Computing", "term": "Semester 1", "day": 1,
    "starts_at": time(10), "ends_at": time(11), "title": "Algorithms", "kind": "class",
    "room": "Seminar 1", "instructor_id": 42, "programme": "BTech", "batch_year": 2025,
}


@pytest.mark.django_db
@pytest.mark.parametrize("same_axis", ["room", "instructor_id", "programme"])
def test_database_excludes_overlaps_on_each_axis(same_axis):
    """BR-DEPT-010/AFR-DEPT-031: overlapping slots cannot persist."""
    TimetableSlot.objects.create(**BASE_SLOT)
    incoming = {**BASE_SLOT, "starts_at": time(10, 30), "ends_at": time(11, 30),
                "room": "Seminar 2", "instructor_id": 53, "programme": "MTech"}
    incoming[same_axis] = BASE_SLOT[same_axis]
    with pytest.raises(IntegrityError), transaction.atomic():
        TimetableSlot.objects.create(**incoming)
    assert TimetableSlot.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_one_overlapping_timetable_slot_commits_when_writes_race(stub_iam):
    """BR-DEPT-010/AFR-DEPT-031: different transactions cannot commit a room conflict."""
    ready = Barrier(2, timeout=10)
    actor = make_principal(kind="staff", active_role="deptadmin_cse", modules=["department"],
                           permissions=[UPDATE_TIMETABLE])
    user = UserRef(actor.user_id, "lab-admin", "Lab admin", "staff", department="CSE")
    stub_iam(users={actor.user_id: user})
    slot = {key: value for key, value in BASE_SLOT.items() if key != "department"}

    def insert(instructor_id):
        try:
            ready.wait()
            upload_timetable(actor=actor, slots=[{**slot, "instructor_id": instructor_id}])
        except ConflictError:
            return "refused"
        else:
            return "saved"
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(insert, (42, 43))) == ["refused", "saved"]
    assert TimetableSlot.objects.count() == 1


@pytest.mark.django_db
def test_throttle_applies_to_department_writes_but_not_reads(monkeypatch, stub_iam):
    monkeypatch.setitem(PrincipalScopedThrottle.THROTTLE_RATES, "department_write", "1/min")
    session = make_session(modules=["department"], permissions=[SUBMIT_FEEDBACK, VIEW_ANNOUNCEMENT])
    user = UserRef(session.user_id, "student", "Student", "student", department="Computing")
    stub_iam(session=session, users={session.user_id: user})
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-session")

    assert client.post("/api/v1/department/feedback", {"content": "First"}, format="json").status_code == 201
    assert client.post("/api/v1/department/feedback", {"content": "Second"}, format="json").status_code == 429
    assert client.get("/api/v1/department/announcements").status_code == 200
    assert Feedback.objects.count() == 1


DEPARTMENT_METHODS = [
    (pattern.name, method, dict.fromkeys(pattern.pattern.converters, 1))
    for pattern in urlpatterns
    for method in ("get", "post", "put")
    if hasattr(pattern.callback.cls, method)
]


@pytest.mark.parametrize(("name", "method", "kwargs"), DEPARTMENT_METHODS)
@pytest.mark.parametrize("missing", ["module", "permission"])
def test_every_department_method_requires_two_gates(stub_iam, name, method, kwargs, missing):
    grants = {code for codes in ROLE_GRANTS.values() for code in codes}
    stub_iam(session=make_session(
        kind="faculty", active_role="HOD (CSE)", roles=["faculty", "HOD (CSE)"],
        modules=[] if missing == "module" else ["department"],
        permissions=grants if missing == "module" else [],
    ))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-session")

    assert getattr(client, method)(reverse(name, kwargs=kwargs)).status_code == 403


@pytest.mark.django_db
def test_cookie_authenticated_feedback_requires_csrf(settings, stub_iam):
    session = make_session(modules=["department"], permissions=[SUBMIT_FEEDBACK])
    user = UserRef(session.user_id, "student", "Student", "student", department="Computing")
    stub_iam(session=session, users={session.user_id: user})
    client = APIClient()
    client.cookies[settings.IAM_AUTH_COOKIE_NAME] = "test-session"
    payload = {"content": "Feedback"}

    assert client.post(reverse("department-feedback"), payload, format="json").status_code == 403
    assert not Feedback.objects.exists()
    accepted = client.post(reverse("department-feedback"), payload, format="json",
                           HTTP_X_CSRF_TOKEN=token_for("test-session"))
    assert accepted.status_code == 201
    assert Feedback.objects.count() == 1
