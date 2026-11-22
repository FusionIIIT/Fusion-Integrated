from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.mms.models import (
    RegistrationWindow,
    StudentRegistration,
    VacationResponse,
    VacationSurvey,
)

pytestmark = pytest.mark.django_db


def client(stub_iam, *, user_id=1001, permissions=(), roles=("student",), kind="student"):
    stub_iam(
        make_session(
            user_id=user_id, kind=kind, roles=roles, modules=("mms",), permissions=permissions
        )
    )
    result = APIClient()
    result.credentials(HTTP_AUTHORIZATION="Token abc")
    return result


def test_student_registration_uses_the_authenticated_identity(stub_iam):
    now = timezone.now()
    RegistrationWindow.objects.create(
        cycle="semester-2026",
        opens_at=now - timedelta(days=1),
        closes_at=now + timedelta(days=1),
        created_by_user_id=9,
    )
    response = client(stub_iam, permissions=("mms.registration.self",)).post(
        "/api/v1/mms/registrations/",
        {"cycle": "semester-2026", "request_type": "register", "user_id": 777},
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["user_id"] == 1001
    assert not StudentRegistration.objects.filter(user_id=777).exists()


def test_warden_can_view_but_cannot_decide_registration(stub_iam):
    pending = StudentRegistration.objects.create(
        user_id=1001, cycle="semester-2026", request_type="register"
    )
    response = client(
        stub_iam,
        user_id=9,
        kind="staff",
        roles=("mess_warden",),
        permissions=("mms.registration.view",),
    ).post(
        f"/api/v1/mms/registrations/{pending.id}/decision/", {"decision": "approve"}, format="json"
    )
    assert response.status_code == 403
    pending.refresh_from_db()
    assert pending.status == StudentRegistration.Status.PENDING


def test_mess_admin_cannot_read_feedback(stub_iam):
    response = client(
        stub_iam, user_id=9, kind="staff", roles=("mess_admin",), permissions=("mms.role.assign",)
    ).get("/api/v1/mms/feedback/")
    assert response.status_code == 403


def test_caretaker_permission_without_active_assignment_cannot_open_window(stub_iam):
    response = client(
        stub_iam,
        user_id=9,
        kind="staff",
        roles=("mess_caretaker",),
        permissions=("mms.registration.decide",),
    ).post(
        "/api/v1/mms/registration-windows/",
        {
            "cycle": "semester-2026",
            "opens_at": timezone.now().isoformat(),
            "closes_at": (timezone.now() + timedelta(days=1)).isoformat(),
        },
        format="json",
    )
    assert response.status_code == 403
    assert not RegistrationWindow.objects.exists()


def test_role_assignment_switches_the_active_caretaker_immediately():
    from modules.mms.services.workflows import assign_role

    now = timezone.now()
    old = assign_role(role="caretaker", user_id=101, actor_id=9, ends_at=now + timedelta(days=2))
    new = assign_role(role="caretaker", user_id=202, actor_id=9, ends_at=now + timedelta(days=5))
    old.refresh_from_db()
    assert old.ends_at <= new.starts_at
    assert new.user_id == 202


def test_survey_default_records_no_only_after_deadline():
    from modules.mms.services.workflows import apply_vacation_defaults

    survey = VacationSurvey.objects.create(
        title="Winter break",
        vacation_start=timezone.localdate(),
        vacation_end=timezone.localdate() + timedelta(days=3),
        response_deadline=timezone.now() - timedelta(minutes=1),
        created_by_user_id=9,
    )
    row = VacationResponse.objects.create(survey=survey, user_id=1001)
    assert apply_vacation_defaults() == 1
    row.refresh_from_db()
    assert (row.response, row.defaulted) == ("no", True)
