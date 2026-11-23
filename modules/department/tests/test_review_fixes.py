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
    stub_iam(users={actor.user_id: user, **{
        uid: UserRef(uid, f"faculty{uid}", "Instructor", "faculty", department="CSE")
        for uid in (42, 43)
    }})
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


@pytest.mark.parametrize(("name", "method", "kwargs"), DEPARTMENT_METHODS)
def test_anonymous_department_requests_require_authentication(name, method, kwargs):
    response = getattr(APIClient(), method)(reverse(name, kwargs=kwargs))
    assert response.status_code == 401


DEPARTMENT_WRITES = [
    (name, method, kwargs, pattern.callback.cls.write_permission)
    for name, method, kwargs in DEPARTMENT_METHODS if method != "get"
    for pattern in urlpatterns if pattern.name == name
]


@pytest.mark.parametrize(("name", "method", "kwargs", "permission"), DEPARTMENT_WRITES)
def test_every_write_refuses_invalid_payload_and_throttles(
    name, method, kwargs, permission, stub_iam, monkeypatch,
):
    code = permission[0] if isinstance(permission, tuple) else permission
    role = next(role for role, grants in ROLE_GRANTS.items() if code in grants)
    stub_iam(session=make_session(active_role=role, roles=[role], permissions=[code],
                                  modules=["department"]))
    monkeypatch.setitem(PrincipalScopedThrottle.THROTTLE_RATES, "department_write", "1/min")
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test-session")
    submit = getattr(client, method)
    url = reverse(name, kwargs=kwargs)
    assert submit(url, {"unknown_key": 1}, format="json").status_code == 400
    assert submit(url, {}, format="json").status_code == 429


@pytest.mark.parametrize("attributes", [
    None, {"department": "ECE"}, {"kind": "student"}, {"is_active": False},
])
@pytest.mark.django_db
def test_slot_requires_an_active_faculty_member_in_scope(stub_iam, attributes):
    from core.api.exceptions import NotFoundError

    actor = make_principal(kind="staff", active_role="deptadmin_cse", modules=["department"],
                           permissions=[UPDATE_TIMETABLE])
    users = {actor.user_id: UserRef(actor.user_id, "admin", "Admin", "staff", department="CSE")}
    if attributes is not None:
        fields = {"department": "CSE", "kind": "faculty", **attributes}
        users[42] = UserRef(42, "faculty", "Instructor", **fields)
    stub_iam(users=users)
    with pytest.raises(NotFoundError):
        upload_timetable(actor=actor, slots=[{k: v for k, v in BASE_SLOT.items() if k != "department"}])
    assert not TimetableSlot.objects.exists()


def test_slot_rejects_id_outside_the_storage_range():
    from modules.department.api.administration import DepartmentTimetableSerializer

    values = {k: v for k, v in BASE_SLOT.items() if k != "department"}
    serializer = DepartmentTimetableSerializer(data={**values, "instructor_id": 2 ** 31})
    assert not serializer.is_valid()
    assert set(serializer.errors) == {"instructor_id"}


@pytest.mark.django_db
def test_direct_service_requires_iam_permission(stub_iam):
    from core.api.exceptions import PermissionDeniedError
    from modules.department.services import submit_feedback

    actor = make_principal(kind="faculty", active_role="faculty", modules=["department"])
    stub_iam(users={actor.user_id: UserRef(actor.user_id, "faculty", "Faculty", "faculty",
                                           department="CSE")})
    with pytest.raises(PermissionDeniedError):
        submit_feedback(actor=actor, content="Review equipment")
    assert not Feedback.objects.exists()


@pytest.mark.django_db
def test_readiness_explains_missing_configuration_and_checks_registration(settings):
    from django.core.management import call_command
    from django.core.management.base import CommandError

    settings.IAM_SERVICE_TOKEN = ""
    with pytest.raises(CommandError, match="IAM_SERVICE_TOKEN"):
        call_command("department_readiness")
    settings.IAM_SERVICE_TOKEN = "test-only-directory-token"
    with pytest.raises(CommandError, match="seed_modules"):
        call_command("department_readiness")
    call_command("seed_modules")
    call_command("department_readiness")
