from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory import contracts as directory
from modules.mms.models import (
    Enrollment,
    Feedback,
    RoleAssignment,
    VacationResponse,
    VacationSurvey,
)

pytestmark = pytest.mark.django_db

MODULE = ("mms",)


def _client(stub_iam, user_id, permissions, kind="student",
            active_role="student"):
    stub_iam(make_session(
        user_id=user_id,
        kind=kind,
        modules=MODULE,
        permissions=permissions,
        active_role=active_role,
        roles=(active_role,),
    ))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    return client


def test_role_reassignment_rejects_conflicting_current_assignment(
        stub_iam, monkeypatch):
    monkeypatch.setattr(directory, "get_users",
                        lambda ids: {uid: object() for uid in ids})
    monkeypatch.setattr(directory, "held_employee_ids",
                        lambda: {202, 303})
    now = timezone.now()
    RoleAssignment.objects.create(
        role="caretaker", user_id=202, starts_at=now - timedelta(days=1),
        ends_at=now + timedelta(days=30), is_current=True,
        assigned_by_user_id=101)

    client = _client(
        stub_iam, 101, ("mms.roles.manage",), kind="staff",
        active_role="mess_admin")
    response = client.post("/api/v1/mms/roles", {
        "role": "caretaker",
        "user_id": 303,
        "starts_at": (now - timedelta(hours=1)).isoformat(),
        "ends_at": (now + timedelta(days=30)).isoformat(),
    }, format="json")

    assert response.status_code == 409
    assert RoleAssignment.objects.get(role="caretaker", is_current=True).user_id == 202


def test_menu_accepts_deletion_with_fewer_entries(stub_iam):
    now = timezone.now()
    caretaker = 202
    RoleAssignment.objects.create(
        role="caretaker", user_id=caretaker,
        starts_at=now - timedelta(days=1), ends_at=now + timedelta(days=30),
        is_current=True, assigned_by_user_id=101)
    client = _client(
        stub_iam, caretaker, (
            "mms.operations.view",
            "mms.menu.manage",
        ), kind="faculty", active_role="mess_caretaker")
    entries = [
        {"day": day, "meal": meal, "item": f"Item {day}-{meal}"}
        for day in range(7)
        for meal in ("breakfast", "lunch", "dinner")
    ]
    entries.pop()

    response = client.post("/api/v1/mms/menu", {
        "week_start": timezone.localdate().isoformat(),
        "entries": entries,
    }, format="json")

    assert response.status_code == 201


def test_student_cannot_list_feedback_review(stub_iam):
    Feedback.objects.create(user_id=1001, message="Service feedback")
    client = _client(stub_iam, 1001, ("mms.student.use",))

    response = client.get("/api/v1/mms/feedback")

    assert response.status_code == 403
    assert not Feedback.objects.filter(user_id=9999).exists()


def test_vacation_accepts_yes_and_no_case_insensitively(stub_iam):
    student = 1001
    Enrollment.objects.create(
        user_id=student, registered_at=timezone.now())
    survey = VacationSurvey.objects.create(
        title="Vacation", vacation_starts_on=timezone.localdate() + timedelta(days=30),
        vacation_ends_on=timezone.localdate() + timedelta(days=37),
        deadline=timezone.now() + timedelta(days=7),
        created_by_user_id=202)
    client = _client(stub_iam, student, ("mms.student.use",))

    yes_response = client.post(
        f"/api/v1/mms/vacation-surveys/{survey.pk}/responses",
        {"response": "Yes"}, format="json")
    assert yes_response.status_code == 200
    assert VacationResponse.objects.get(
        survey=survey, user_id=student).response == "yes"

    no_response = client.post(
        f"/api/v1/mms/vacation-surveys/{survey.pk}/responses",
        {"response": "NO"}, format="json")
    assert no_response.status_code == 200
    assert VacationResponse.objects.get(
        survey=survey, user_id=student).response == "no"


def test_warden_can_view_supervisory_report_types(stub_iam):
    warden = 303
    now = timezone.now()
    RoleAssignment.objects.create(
        role="warden", user_id=warden,
        starts_at=now - timedelta(days=1), ends_at=now + timedelta(days=30),
        is_current=True, assigned_by_user_id=101)
    client = _client(
        stub_iam, warden, (
            "mms.operations.view",
            "mms.reports.warden",
        ), kind="faculty", active_role="mess_warden")

    registered = client.get("/api/v1/mms/reports?type=registered")
    rebates = client.get("/api/v1/mms/reports?type=rebates")
    vacation = client.get("/api/v1/mms/reports?type=vacation")

    assert registered.status_code == 200
    assert rebates.status_code == 200
    assert vacation.status_code == 200
