import json
from datetime import datetime, time, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.mms.models import (
    Enrollment,
    MonthlyBill,
    NotificationOutbox,
    RebateRequest,
    RoleAssignment,
    SpecialFoodRequest,
    StudentRequest,
    VacationResponse,
)

pytestmark = pytest.mark.django_db

STUDENT_ID = 1001
CARETAKER_ID = 9001
WF_DESIGN_PATH = Path(__file__).resolve().parents[3] / "a8_design" / "WF_DESIGN.json"
WF_DESIGN = json.loads(WF_DESIGN_PATH.read_text(encoding="utf-8"))
BLOCKED_CASES = {
    case["test_id"]: case["reason"] for case in WF_DESIGN["blocked_cases"]
}


def _assert_frozen_testable_case(test_case_id):
    case = next(case for case in WF_DESIGN["test_cases"]
                if case["test_id"] == test_case_id)
    assert case["status"] == "TESTABLE"


def _client(stub_iam, *, user_id, role, permissions):
    stub_iam(make_session(
        user_id=user_id,
        kind="student" if role == "student" else "staff",
        modules=("mess_management",),
        permissions=permissions,
        roles=(role,),
        active_role=role,
    ))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token wf-test")
    return client


def _student_client(stub_iam, user_id=STUDENT_ID):
    return _client(
        stub_iam,
        user_id=user_id,
        role="student",
        permissions=("mess_management.student.use",),
    )


def _caretaker_client(stub_iam, user_id=CARETAKER_ID, permission=None):
    permissions = {permission} if permission else set()
    return _client(
        stub_iam,
        user_id=user_id,
        role="caretaker",
        permissions=permissions,
    )


@pytest.fixture
def active_caretaker():
    now = timezone.now()
    RoleAssignment.objects.create(
        role="caretaker",
        user_id=CARETAKER_ID,
        starts_at=now - timedelta(days=1),
        ends_at=now + timedelta(days=365),
        is_current=True,
        assigned_by_user_id=8001,
    )
    return CARETAKER_ID


def _registered_student(user_id=STUDENT_ID, *, registered_at=None):
    return Enrollment.objects.create(
        user_id=user_id,
        registered_at=registered_at or timezone.now() - timedelta(days=1),
    )


def _notification_topics(user_id):
    return set(NotificationOutbox.objects.filter(
        recipient_user_id=user_id,
    ).values_list("topic", flat=True))


def _open_registration_window(stub_iam, active_caretaker):
    now = timezone.now()
    response = _caretaker_client(
        stub_iam,
        active_caretaker,
        "mess_management.operations.manage",
    ).post(
        "/api/v1/mms/registration-windows",
        {
            "cycle": "WF-cycle",
            "opens_at": (now - timedelta(days=1)).isoformat(),
            "closes_at": (now + timedelta(days=5)).isoformat(),
        },
        format="json",
    )
    assert response.status_code == 201, response.content
    return response.json()


def _create_vacation_survey(stub_iam, active_caretaker, *, title="WF vacation"):
    now = timezone.now()
    response = _caretaker_client(
        stub_iam,
        active_caretaker,
        "mess_management.surveys.manage",
    ).post(
        "/api/v1/mms/vacation-surveys",
        {
            "title": title,
            "vacation_starts_on": (timezone.localdate() + timedelta(days=30)).isoformat(),
            "vacation_ends_on": (timezone.localdate() + timedelta(days=35)).isoformat(),
            "deadline": (now + timedelta(hours=1)).isoformat(),
        },
        format="json",
    )
    assert response.status_code == 201, response.content
    return response.json()


def _create_special_food(stub_iam, *, user_id=STUDENT_ID):
    response = _student_client(stub_iam, user_id).post(
        "/api/v1/mms/special-food",
        {
            "reason": "illness",
            "details": "WF scenario",
            "requested_for": (timezone.localdate() + timedelta(days=1)).isoformat(),
        },
        format="json",
    )
    assert response.status_code == 201, response.content
    return response.json()


def _approve_special_food(stub_iam, active_caretaker, request_id):
    response = _caretaker_client(
        stub_iam,
        active_caretaker,
        "mess_management.requests.review",
    ).post(
        f"/api/v1/mms/special-food/{request_id}/decision",
        {"approve": True, "charge_amount": "1.00"},
        format="json",
    )
    assert response.status_code == 200, response.content
    return response.json()


@pytest.mark.parametrize("test_case_id", ["TC-WF-001"], ids=["TC-WF-001"])
def test_tc_wf_001_registration_approved(test_case_id, stub_iam, active_caretaker):
    _assert_frozen_testable_case(test_case_id)
    window = _open_registration_window(stub_iam, active_caretaker)

    submitted = _student_client(stub_iam).post(
        "/api/v1/mms/requests",
        {"kind": "registration", "window_id": window["id"]},
        format="json",
    )
    assert submitted.status_code == 201, submitted.content
    assert submitted.json()["status"] == "pending"

    decision = _caretaker_client(
        stub_iam,
        active_caretaker,
        "mess_management.requests.review",
    ).post(
        f"/api/v1/mms/requests/{submitted.json()['id']}/decision",
        {"approve": True},
        format="json",
    )
    assert decision.status_code == 200, decision.content
    assert decision.json()["status"] == "approved"
    assert Enrollment.objects.get(user_id=STUDENT_ID).is_registered
    assert list(StudentRequest.objects.get(pk=submitted.json()["id"])
                .history.values_list("status", flat=True)) == ["pending", "approved"]
    assert _notification_topics(STUDENT_ID) == {"request.submitted", "request.decided"}


@pytest.mark.parametrize("test_case_id", ["TC-WF-002"], ids=["TC-WF-002"])
def test_tc_wf_002_registration_rejected(test_case_id, stub_iam, active_caretaker):
    _assert_frozen_testable_case(test_case_id)
    window = _open_registration_window(stub_iam, active_caretaker)
    submitted = _student_client(stub_iam).post(
        "/api/v1/mms/requests",
        {"kind": "registration", "window_id": window["id"]},
        format="json",
    )
    assert submitted.status_code == 201, submitted.content

    decision = _caretaker_client(
        stub_iam,
        active_caretaker,
        "mess_management.requests.review",
    ).post(
        f"/api/v1/mms/requests/{submitted.json()['id']}/decision",
        {"approve": False},
        format="json",
    )
    assert decision.status_code == 200, decision.content
    assert decision.json()["status"] == "rejected"
    assert not Enrollment.objects.filter(user_id=STUDENT_ID).exists()
    assert list(StudentRequest.objects.get(pk=submitted.json()["id"])
                .history.values_list("status", flat=True)) == ["pending", "rejected"]
    assert _notification_topics(STUDENT_ID) == {"request.submitted", "request.decided"}


@pytest.mark.parametrize("test_case_id", ["TC-WF-004"], ids=["TC-WF-004"])
def test_tc_wf_004_deregistration_approved_next_calendar_day(
    test_case_id,
    stub_iam,
    active_caretaker,
):
    _assert_frozen_testable_case(test_case_id)
    enrollment = _registered_student()
    submitted = _student_client(stub_iam).post(
        "/api/v1/mms/requests",
        {"kind": "deregistration"},
        format="json",
    )
    assert submitted.status_code == 201, submitted.content

    decision = _caretaker_client(
        stub_iam,
        active_caretaker,
        "mess_management.requests.review",
    ).post(
        f"/api/v1/mms/requests/{submitted.json()['id']}/decision",
        {"approve": True},
        format="json",
    )
    assert decision.status_code == 200, decision.content
    approved = StudentRequest.objects.get(pk=submitted.json()["id"])
    assert approved.status == "approved_awaiting_effect"
    enrollment.refresh_from_db()
    assert enrollment.deregistered_at is None

    from modules.mms.services.operations import activate_deregistrations

    assert activate_deregistrations(now=approved.effective_at) == 1
    enrollment.refresh_from_db()
    approved.refresh_from_db()
    assert enrollment.deregistered_at == approved.effective_at
    assert approved.status == "effective"


@pytest.mark.parametrize("test_case_id", ["TC-WF-005"], ids=["TC-WF-005"])
def test_tc_wf_005_deregistration_rejected(test_case_id, stub_iam, active_caretaker):
    _assert_frozen_testable_case(test_case_id)
    enrollment = _registered_student()
    submitted = _student_client(stub_iam).post(
        "/api/v1/mms/requests",
        {"kind": "deregistration"},
        format="json",
    )
    assert submitted.status_code == 201, submitted.content

    decision = _caretaker_client(
        stub_iam,
        active_caretaker,
        "mess_management.requests.review",
    ).post(
        f"/api/v1/mms/requests/{submitted.json()['id']}/decision",
        {"approve": False},
        format="json",
    )
    assert decision.status_code == 200, decision.content
    assert decision.json()["status"] == "rejected"
    enrollment.refresh_from_db()
    assert enrollment.deregistered_at is None
    assert enrollment.is_registered


@pytest.mark.parametrize("test_case_id", ["TC-WF-006"], ids=["TC-WF-006"])
def test_tc_wf_006_rebate_approved_as_submitted(test_case_id, stub_iam, active_caretaker):
    _assert_frozen_testable_case(test_case_id)
    _registered_student()
    today = timezone.localdate()
    reasons = [
        ("medical", "", 1),
        ("institute_leave", "", 4),
        ("family_function", "", 7),
        ("other", "WF required explanation", 10),
    ]

    for reason, explanation, offset in reasons:
        starts_on = today + timedelta(days=offset)
        ends_on = starts_on + timedelta(days=2)
        submitted = _student_client(stub_iam).post(
            "/api/v1/mms/rebates",
            {
                "reason": reason,
                "explanation": explanation,
                "starts_on": starts_on.isoformat(),
                "ends_on": ends_on.isoformat(),
            },
            format="json",
        )
        assert submitted.status_code == 201, submitted.content
        assert submitted.json()["status"] == "pending"

        decision = _caretaker_client(
            stub_iam,
            active_caretaker,
            "mess_management.requests.review",
        ).post(
            f"/api/v1/mms/rebates/{submitted.json()['id']}/decision",
            {"approve": True},
            format="json",
        )
        assert decision.status_code == 200, decision.content
        assert decision.json()["status"] == "approved"
        assert decision.json()["starts_on"] == starts_on.isoformat()
        assert decision.json()["ends_on"] == ends_on.isoformat()

    assert RebateRequest.objects.count() == 4
    assert NotificationOutbox.objects.filter(
        recipient_user_id=STUDENT_ID,
        topic__in=("rebate.submitted", "rebate.decided"),
    ).count() == 8


@pytest.mark.parametrize("test_case_id", ["TC-WF-008"], ids=["TC-WF-008"])
def test_tc_wf_008_rebate_rejected(test_case_id, stub_iam, active_caretaker):
    _assert_frozen_testable_case(test_case_id)
    _registered_student()
    today = timezone.localdate()
    submitted = _student_client(stub_iam).post(
        "/api/v1/mms/rebates",
        {
            "reason": "medical",
            "explanation": "",
            "starts_on": (today + timedelta(days=1)).isoformat(),
            "ends_on": (today + timedelta(days=3)).isoformat(),
        },
        format="json",
    )
    assert submitted.status_code == 201, submitted.content

    decision = _caretaker_client(
        stub_iam,
        active_caretaker,
        "mess_management.requests.review",
    ).post(
        f"/api/v1/mms/rebates/{submitted.json()['id']}/decision",
        {"approve": False},
        format="json",
    )
    assert decision.status_code == 200, decision.content
    assert decision.json()["status"] == "rejected"
    assert not MonthlyBill.objects.exists()
    assert _notification_topics(STUDENT_ID) == {"rebate.submitted", "rebate.decided"}


@pytest.mark.parametrize("test_case_id", ["TC-WF-013"], ids=["TC-WF-013"])
def test_tc_wf_013_vacation_survey_yes_and_registered_recipients(
    test_case_id,
    stub_iam,
    active_caretaker,
):
    _assert_frozen_testable_case(test_case_id)
    _registered_student()
    _registered_student(2002, registered_at=timezone.now() - timedelta(days=1))
    Enrollment.objects.filter(user_id=2002).update(deregistered_at=timezone.now())

    survey = _create_vacation_survey(stub_iam, active_caretaker)
    assert set(NotificationOutbox.objects.filter(
        topic="vacation.created",
    ).values_list("recipient_user_id", flat=True)) == {STUDENT_ID}

    rows = _student_client(stub_iam).get("/api/v1/mms/vacation-surveys").json()["results"]
    assert [row["id"] for row in rows] == [survey["id"]]
    response = _student_client(stub_iam).post(
        f"/api/v1/mms/vacation-surveys/{survey['id']}/responses",
        {"response": "yes"},
        format="json",
    )
    assert response.status_code == 200, response.content
    assert response.json()["response"] == "yes"
    assert not response.json()["is_default"]


@pytest.mark.parametrize("test_case_id", ["TC-WF-014"], ids=["TC-WF-014"])
def test_tc_wf_014_vacation_survey_explicit_no(test_case_id, stub_iam, active_caretaker):
    _assert_frozen_testable_case(test_case_id)
    _registered_student()
    survey = _create_vacation_survey(stub_iam, active_caretaker)

    response = _student_client(stub_iam).post(
        f"/api/v1/mms/vacation-surveys/{survey['id']}/responses",
        {"response": "no"},
        format="json",
    )
    assert response.status_code == 200, response.content
    assert response.json()["response"] == "no"
    assert not response.json()["is_default"]


@pytest.mark.parametrize("test_case_id", ["TC-WF-015"], ids=["TC-WF-015"])
def test_tc_wf_015_vacation_survey_default_no_at_deadline(
    test_case_id,
    stub_iam,
    active_caretaker,
):
    _assert_frozen_testable_case(test_case_id)
    from modules.mms.services.operations import default_vacation_responses

    _registered_student()
    survey = _create_vacation_survey(stub_iam, active_caretaker)
    deadline = datetime.fromisoformat(survey["deadline"])

    assert default_vacation_responses(now=deadline) == 1
    response = VacationResponse.objects.get(
        survey_id=survey["id"],
        user_id=STUDENT_ID,
    )
    assert response.response == "no"
    assert response.is_default


@pytest.mark.parametrize("test_case_id", ["TC-WF-017"], ids=["TC-WF-017"])
def test_tc_wf_017_special_food_rejected_by_caretaker(
    test_case_id,
    stub_iam,
    active_caretaker,
):
    _assert_frozen_testable_case(test_case_id)
    submitted = _create_special_food(stub_iam)
    assert submitted["status"] == "requested"

    decision = _caretaker_client(
        stub_iam,
        active_caretaker,
        "mess_management.requests.review",
    ).post(
        f"/api/v1/mms/special-food/{submitted['id']}/decision",
        {"approve": False},
        format="json",
    )
    assert decision.status_code == 200, decision.content
    assert decision.json()["status"] == "rejected"
    assert _notification_topics(STUDENT_ID) == {
        "special_food.submitted",
        "special_food.decided",
    }


@pytest.mark.parametrize("test_case_id", ["TC-WF-019"], ids=["TC-WF-019"])
def test_tc_wf_019_special_food_approved_awaiting_fulfillment(
    test_case_id,
    stub_iam,
    active_caretaker,
):
    _assert_frozen_testable_case(test_case_id)
    submitted = _create_special_food(stub_iam)
    approved = _approve_special_food(stub_iam, active_caretaker, submitted["id"])
    assert approved["status"] == "approved"
    assert approved["charge_amount"] == "1.00"
    assert _notification_topics(STUDENT_ID) == {
        "special_food.submitted",
        "special_food.decided",
    }


@pytest.mark.parametrize("test_case_id", ["TC-WF-020"], ids=["TC-WF-020"])
def test_tc_wf_020_special_food_served(test_case_id, stub_iam, active_caretaker):
    _assert_frozen_testable_case(test_case_id)
    submitted = _create_special_food(stub_iam)
    _approve_special_food(stub_iam, active_caretaker, submitted["id"])

    response = _caretaker_client(
        stub_iam,
        active_caretaker,
        "mess_management.requests.review",
    ).post(
        f"/api/v1/mms/special-food/{submitted['id']}/fulfillment",
        {"status": "served"},
        format="json",
    )
    assert response.status_code == 200, response.content
    assert response.json()["status"] == "served"
    assert "special_food.fulfillment" in _notification_topics(STUDENT_ID)


@pytest.mark.parametrize("test_case_id", ["TC-WF-021"], ids=["TC-WF-021"])
def test_tc_wf_021_special_food_cancelled(test_case_id, stub_iam, active_caretaker):
    _assert_frozen_testable_case(test_case_id)
    submitted = _create_special_food(stub_iam)
    _approve_special_food(stub_iam, active_caretaker, submitted["id"])

    response = _caretaker_client(
        stub_iam,
        active_caretaker,
        "mess_management.requests.review",
    ).post(
        f"/api/v1/mms/special-food/{submitted['id']}/fulfillment",
        {"status": "cancelled"},
        format="json",
    )
    assert response.status_code == 200, response.content
    assert response.json()["status"] == "cancelled"
    assert "special_food.fulfillment" in _notification_topics(STUDENT_ID)


@pytest.mark.parametrize("test_case_id", ["TC-WF-023"], ids=["TC-WF-023"])
def test_tc_wf_023_monthly_billing_generated_finalized_and_published(
    test_case_id,
    stub_iam,
    active_caretaker,
):
    _assert_frozen_testable_case(test_case_id)
    from modules.mms.services.operations import generate_ready_bills

    this_month = timezone.localdate().replace(day=1)
    previous_month = this_month - timedelta(days=1)
    bill_period = previous_month.replace(day=1)
    period_start = timezone.make_aware(datetime.combine(bill_period, time.min))
    enrollment = _registered_student(registered_at=period_start)
    RebateRequest.objects.create(
        user_id=enrollment.user_id,
        reason="medical",
        explanation="",
        starts_on=previous_month,
        ends_on=previous_month,
        status="approved",
    )
    SpecialFoodRequest.objects.create(
        user_id=enrollment.user_id,
        reason="illness",
        details="WF billing input",
        requested_for=previous_month,
        status="approved",
        charge_amount=Decimal("1.00"),
    )

    inputs = _caretaker_client(
        stub_iam,
        active_caretaker,
        "mess_management.billing.manage",
    ).post(
        "/api/v1/mms/billing-inputs",
        {
            "year": previous_month.year,
            "month": previous_month.month,
            "students": [{
                "user_id": enrollment.user_id,
                "daily_rate": "100.00",
                "served_days": 1,
            }],
        },
        format="json",
    )
    assert inputs.status_code == 200, inputs.content
    assert inputs.json()["saved"] == 1

    assert generate_ready_bills(today=this_month) == 1
    bill = MonthlyBill.objects.get(user_id=STUDENT_ID)
    assert bill.status == "generated"

    finalize = _caretaker_client(
        stub_iam,
        active_caretaker,
        "mess_management.billing.manage",
    ).post(f"/api/v1/mms/bills/{bill.pk}/finalize", {}, format="json")
    assert finalize.status_code == 200, finalize.content
    assert finalize.json()["status"] == "finalized"

    publish = _caretaker_client(
        stub_iam,
        active_caretaker,
        "mess_management.billing.manage",
    ).post(f"/api/v1/mms/bills/{bill.pk}/publish", {}, format="json")
    assert publish.status_code == 200, publish.content
    assert publish.json()["status"] == "published"

    student_bills = _student_client(stub_iam).get("/api/v1/mms/bills")
    assert student_bills.status_code == 200, student_bills.content
    assert [row["status"] for row in student_bills.json()["results"]] == ["published"]
    assert Decimal(str(student_bills.json()["balance"])) == Decimal(
        student_bills.json()["results"][0]["total"],
    )
    assert "bill.published" in _notification_topics(STUDENT_ID)


@pytest.mark.parametrize(
    "test_id",
    sorted(BLOCKED_CASES, key=lambda value: int(value.rsplit("-", 1)[1])),
    ids=lambda test_id: test_id,
)
def test_frozen_blocked_workflow_case(test_id):
    pytest.skip(f"{test_id}: {BLOCKED_CASES[test_id]}")
