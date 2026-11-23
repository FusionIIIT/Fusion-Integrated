from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory import contracts as directory
from modules.mms.models import (
    Enrollment,
    Feedback,
    RegistrationWindow,
    RoleAssignment,
    SpecialFoodHistory,
    SpecialFoodRequest,
    StudentRequest,
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


def test_midcycle_role_reassignment_retires_incumbent_at_effective_time(
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
    effective_at = now - timedelta(hours=1)
    response = client.post("/api/v1/mms/roles", {
        "role": "caretaker",
        "user_id": 303,
        "starts_at": effective_at.isoformat(),
        "ends_at": (now + timedelta(days=30)).isoformat(),
    }, format="json")

    assert response.status_code == 201
    incumbent = RoleAssignment.objects.get(role="caretaker", user_id=202)
    replacement = RoleAssignment.objects.get(role="caretaker", user_id=303)
    assert incumbent.ends_at == effective_at
    assert incumbent.is_current is False
    assert replacement.starts_at == effective_at
    assert replacement.is_current is True
    assert RoleAssignment.objects.filter(
        role="caretaker", is_current=True).count() == 1


def test_reassigned_caretaker_can_see_and_act_on_pending_requests(
        stub_iam, monkeypatch):
    monkeypatch.setattr(directory, "get_users",
                        lambda ids: {uid: object() for uid in ids})
    monkeypatch.setattr(directory, "held_employee_ids", lambda: {202, 303})
    now = timezone.now()
    RoleAssignment.objects.create(
        role="caretaker", user_id=202, starts_at=now - timedelta(days=1),
        ends_at=now + timedelta(days=30), is_current=True,
        assigned_by_user_id=101)
    window = RegistrationWindow.objects.create(
        cycle="current", opens_at=now - timedelta(days=1),
        closes_at=now + timedelta(days=1), opened_by_user_id=101)
    request = StudentRequest.objects.create(
        user_id=1001, kind="registration", window=window)
    manager = _client(
        stub_iam, 101, ("mms.roles.manage",), kind="staff",
        active_role="mess_admin")
    reassignment = manager.post("/api/v1/mms/roles", {
        "role": "caretaker", "user_id": 303,
        "starts_at": now.isoformat(),
        "ends_at": (now + timedelta(days=30)).isoformat(),
    }, format="json")
    assert reassignment.status_code == 201

    caretaker = _client(
        stub_iam, 303, ("mms.operations.view", "mms.requests.review"),
        kind="faculty", active_role="mess_caretaker")
    listing = caretaker.get("/api/v1/mms/requests")
    assert listing.status_code == 200
    assert request.pk in {item["id"] for item in listing.json()["results"]}

    decision = caretaker.post(
        f"/api/v1/mms/requests/{request.pk}/decision",
        {"approve": True}, format="json")
    assert decision.status_code == 200
    assert decision.json()["status"] == "approved"


def test_special_food_approval_fails_closed_without_authoritative_charge_policy(
        stub_iam):
    now = timezone.now()
    RoleAssignment.objects.create(
        role="caretaker", user_id=202, starts_at=now - timedelta(days=1),
        ends_at=now + timedelta(days=30), is_current=True,
        assigned_by_user_id=101)
    request = SpecialFoodRequest.objects.create(
        user_id=1001, reason="illness", details="Diet request",
        requested_for=timezone.localdate() + timedelta(days=2))
    SpecialFoodHistory.objects.create(
        request=request, status="requested", actor_user_id=1001)
    client = _client(
        stub_iam, 202, ("mms.requests.review",), kind="faculty",
        active_role="mess_caretaker")

    response = client.post(
        f"/api/v1/mms/special-food/{request.pk}/decision",
        {"approve": True, "charge_amount": "10.00"}, format="json")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "special_food_charge_policy_unavailable"
    request.refresh_from_db()
    assert request.status == "requested"
    assert request.charge_amount is None
    assert list(SpecialFoodHistory.objects.filter(request=request).values_list(
        "status", flat=True)) == ["requested"]


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
