from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory.models import UserRef
from modules.leave_elm.models import (
    HolidayCalendar,
    HolidayDate,
    LeaveApplication,
    LeaveBalance,
    LeaveHierarchy,
    LeaveSLAConfig,
    LeaveYearEndRun,
)
from modules.leave_elm.services import (
    available_balance,
    get_balance,
    process_sla_thresholds,
    process_year_end,
)

pytestmark = pytest.mark.django_db

EMPLOYEE_PERMISSIONS = (
    "leave_elm.apply.self",
    "leave_elm.view.self",
    "leave_elm.cancel.self",
    "leave_elm.extend.self",
    "leave_elm.resume.self",
)


@pytest.fixture
def people():
    UserRef.objects.create(
        user_id=1001, username="employee", display_name="Employee One",
        kind="faculty", department="Engineering",
    )
    UserRef.objects.create(
        user_id=2001, username="unit-head", display_name="Unit Head",
        kind="staff", department="Engineering",
    )
    UserRef.objects.create(
        user_id=3001, username="sanctioner", display_name="Sanctioner",
        kind="staff", department="Administration",
    )
    return {"employee": 1001, "unit_head": 2001, "sanctioner": 3001}


def _client(stub_iam, *, user_id=1001, kind="faculty", roles=(), permissions=()):
    stub_iam(make_session(
        user_id=user_id,
        kind=kind,
        roles=roles,
        modules=("leave_elm",),
        permissions=permissions,
    ))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    return client


def _hierarchy(people, category="CL"):
    return LeaveHierarchy.objects.create(
        department="Engineering",
        category=category,
        unit_head_user_id=people["unit_head"],
        final_authority_user_id=people["sanctioner"],
        updated_by_user_id=9000,
    )


def _request_payload(category="CL", **updates):
    return {
        "category": category,
        "start_date": "2026-12-07",
        "end_date": "2026-12-08",
        "reason": "Personal leave",
        **updates,
    }


def test_application_creation_overlap_and_half_day_cl(stub_iam, people):
    _hierarchy(people)
    client = _client(
        stub_iam, roles=("Faculty",), permissions=EMPLOYEE_PERMISSIONS,
    )
    first = client.post(
        "/api/v1/leave/applications/apply",
        _request_payload(
            start_date="2026-12-07", end_date="2026-12-07",
            half_day_period="first_half",
        ), format="json",
    )
    assert first.status_code == 201
    assert first.json()["status"] == "unit_head_review"

    second = client.post(
        "/api/v1/leave/applications/apply",
        _request_payload(
            start_date="2026-12-07", end_date="2026-12-07",
            half_day_period="second_half",
        ),
        format="json",
    )
    assert second.status_code == 201

    overlap = client.post(
        "/api/v1/leave/applications/apply",
        _request_payload(start_date="2026-12-07", end_date="2026-12-07"),
        format="json",
    )
    assert overlap.status_code == 409
    assert overlap.json()["error"]["code"] == "leave_overlap"
    balance = get_balance(people["employee"], "faculty", "CL", 2026)
    assert available_balance(balance) == Decimal("7")

    reviewer = _client(
        stub_iam, user_id=people["unit_head"], kind="staff",
        roles=("Unit Head",), permissions=("leave_elm.review.unit",),
    )
    approved = reviewer.post(
        f"/api/v1/leave/applications/{first.json()['id']}/decision",
        {"decision": "approve"}, format="json",
    )
    assert approved.status_code == 200
    balance.refresh_from_db()
    assert balance.remaining == Decimal("7.5")
    assert available_balance(balance) == Decimal("7")

    client = _client(
        stub_iam, roles=("Faculty",), permissions=EMPLOYEE_PERMISSIONS,
    )
    withdrawn = client.post(
        f"/api/v1/leave/applications/{second.json()['id']}/withdraw",
    )
    assert withdrawn.status_code == 200
    assert withdrawn.json()["status"] == "withdrawn"


def test_restricted_holiday_requires_published_calendar(stub_iam, people):
    _hierarchy(people, "RH")
    calendar = HolidayCalendar.objects.create(
        name="RH 2026", year=2026, created_by_user_id=9000,
    )
    HolidayDate.objects.create(
        calendar=calendar, date=date(2026, 12, 7), is_restricted=True,
        label="Restricted Holiday",
    )
    client = _client(
        stub_iam, roles=("Faculty",), permissions=EMPLOYEE_PERMISSIONS,
    )
    payload = _request_payload("RH", start_date="2026-12-07", end_date="2026-12-07")
    unpublished = client.post(
        "/api/v1/leave/applications/apply", payload, format="json",
    )
    assert unpublished.status_code == 409
    calendar.publish()
    published = client.post(
        "/api/v1/leave/applications/apply", payload, format="json",
    )
    assert published.status_code == 201


def test_unit_head_approval_deducts_balance_and_rejection_does_not(
        stub_iam, people):
    _hierarchy(people)
    employee = _client(
        stub_iam, roles=("Faculty",), permissions=EMPLOYEE_PERMISSIONS,
    )
    approved = employee.post(
        "/api/v1/leave/applications/apply", _request_payload(), format="json",
    ).json()
    unit_head = _client(
        stub_iam, user_id=people["unit_head"], kind="staff",
        roles=("Unit Head",), permissions=("leave_elm.review.unit",),
    )
    response = unit_head.post(
        f"/api/v1/leave/applications/{approved['id']}/decision",
        {"decision": "approve"}, format="json",
    )
    assert response.status_code == 200
    balance = LeaveBalance.objects.get(
        employee_id=people["employee"], category="CL", year=2026,
    )
    assert balance.remaining == Decimal("6")

    employee = _client(
        stub_iam, roles=("Faculty",), permissions=EMPLOYEE_PERMISSIONS,
    )
    rejected = employee.post(
        "/api/v1/leave/applications/apply",
        _request_payload(start_date="2026-12-14", end_date="2026-12-15"),
        format="json",
    ).json()
    unit_head = _client(
        stub_iam, user_id=people["unit_head"], kind="staff",
        roles=("Unit Head",), permissions=("leave_elm.review.unit",),
    )
    denied = unit_head.post(
        f"/api/v1/leave/applications/{rejected['id']}/decision",
        {"decision": "reject", "note": "Not approved"}, format="json",
    )
    assert denied.status_code == 200
    balance.refresh_from_db()
    assert balance.remaining == Decimal("6")


def test_cancellation_restores_balance(stub_iam, people):
    _hierarchy(people)
    row = LeaveBalance.objects.create(
        employee_id=people["employee"], employee_kind="faculty",
        category="CL", year=2026, entitlement=Decimal("8"),
        used=Decimal("2"), remaining=Decimal("6"),
    )
    parent = LeaveApplication.objects.create(
        employee_id=people["employee"], employee_kind="faculty",
        department="Engineering", category="CL", status="approved",
        start_date=date(2026, 12, 7), end_date=date(2026, 12, 8),
        reason="Personal leave", final_decision_by=people["unit_head"],
        final_decision_at=timezone.now(),
    )
    from modules.leave_elm.models import LeaveLedgerEntry

    LeaveLedgerEntry.objects.create(
        balance=row, entry_type="debit", amount=Decimal("-2"),
        reference=f"leave-debit:{parent.pk}",
    )
    client = _client(
        stub_iam, roles=("Faculty",), permissions=EMPLOYEE_PERMISSIONS,
    )
    requested = client.post(
        f"/api/v1/leave/applications/{parent.pk}/cancel", format="json",
    )
    assert requested.status_code == 201
    cancellation_id = requested.json()["id"]
    reviewer = _client(
        stub_iam, user_id=people["unit_head"], kind="staff",
        roles=("Unit Head",), permissions=("leave_elm.review.unit",),
    )
    response = reviewer.post(
        f"/api/v1/leave/applications/{cancellation_id}/decision",
        {"decision": "approve"}, format="json",
    )
    assert response.status_code == 200
    parent.refresh_from_db()
    row.refresh_from_db()
    assert parent.status == "cancelled"
    assert row.remaining == Decimal("8")


def test_extension_and_early_resumption_adjust_balance(stub_iam, people):
    _hierarchy(people, "EL")
    balance = LeaveBalance.objects.create(
        employee_id=people["employee"], employee_kind="faculty",
        category="EL", year=2026, entitlement=Decimal("30"),
        used=Decimal("5"), remaining=Decimal("25"),
    )
    parent = LeaveApplication.objects.create(
        employee_id=people["employee"], employee_kind="faculty",
        department="Engineering", category="EL", status="approved",
        start_date=timezone.localdate() - timedelta(days=5),
        end_date=timezone.localdate(), reason="Medical leave",
        final_decision_by=people["sanctioner"], final_decision_at=timezone.now(),
    )
    employee = _client(
        stub_iam, roles=("Faculty",), permissions=EMPLOYEE_PERMISSIONS,
    )
    extension = employee.post(
        f"/api/v1/leave/applications/{parent.pk}/extend",
        {"new_end_date": (timezone.localdate() + timedelta(days=2)).isoformat(),
         "reason": "Recovery"},
        format="json",
    )
    assert extension.status_code == 201
    extension_id = extension.json()["id"]
    unit_head = _client(
        stub_iam, user_id=people["unit_head"], kind="staff",
        roles=("Unit Head",), permissions=("leave_elm.review.unit",),
    )
    routed = unit_head.post(
        f"/api/v1/leave/applications/{extension_id}/decision",
        {"decision": "approve", "recommendation": "recommended"},
        format="json",
    )
    assert routed.status_code == 200
    authority = _client(
        stub_iam, user_id=people["sanctioner"], kind="staff",
        roles=("Dean",), permissions=("leave_elm.review.final",),
    )
    approved = authority.post(
        f"/api/v1/leave/applications/{extension_id}/decision",
        {"decision": "approve"}, format="json",
    )
    assert approved.status_code == 200
    parent.refresh_from_db()
    assert parent.end_date == timezone.localdate()
    balance.refresh_from_db()
    assert balance.remaining == Decimal("23")

    employee = _client(
        stub_iam, roles=("Faculty",), permissions=EMPLOYEE_PERMISSIONS,
    )
    resume = employee.post(
        f"/api/v1/leave/applications/{parent.pk}/resumption",
        {"actual_resume_date": timezone.localdate().isoformat(),
         "details": "Returned early"},
        format="json",
    )
    assert resume.status_code == 201
    authority = _client(
        stub_iam, user_id=people["sanctioner"], kind="staff",
        roles=("Dean",), permissions=("leave_elm.review.final",),
    )
    reviewed = authority.post(
        f"/api/v1/leave/resumptions/{resume.json()['id']}/decision",
        {"decision": "approve"}, format="json",
    )
    assert reviewed.status_code == 200
    balance.refresh_from_db()
    assert balance.remaining == Decimal("25")


def test_employee_data_isolation_and_admin_permission(stub_iam, people):
    LeaveApplication.objects.create(
        employee_id=people["employee"], employee_kind="faculty",
        department="Engineering", category="CL", status="approved",
        start_date=date(2026, 12, 7), end_date=date(2026, 12, 7),
        reason="Own",
    )
    LeaveApplication.objects.create(
        employee_id=2002, employee_kind="faculty",
        department="Other", category="CL", status="approved",
        start_date=date(2026, 12, 7), end_date=date(2026, 12, 7),
        reason="Other",
    )
    client = _client(
        stub_iam, roles=("Faculty",), permissions=EMPLOYEE_PERMISSIONS,
    )
    rows = client.get("/api/v1/leave/applications").json()["results"]
    assert [row["employee_id"] for row in rows] == [people["employee"]]
    forbidden = client.get("/api/v1/leave/admin/policies")
    assert forbidden.status_code == 403


def test_year_end_lapse_carry_and_fractional_vl_conversion(people):
    faculty = people["employee"]
    LeaveBalance.objects.create(
        employee_id=faculty, employee_kind="faculty", category="VL",
        year=2026, entitlement=Decimal("60"), used=Decimal("52.5"),
        remaining=Decimal("7.5"),
    )
    LeaveBalance.objects.create(
        employee_id=faculty, employee_kind="faculty", category="EL",
        year=2026, entitlement=Decimal("0"), used=Decimal("2"),
        remaining=Decimal("5"),
    )
    LeaveBalance.objects.create(
        employee_id=faculty, employee_kind="faculty", category="CL",
        year=2026, entitlement=Decimal("8"), used=Decimal("2"),
        remaining=Decimal("6"),
    )
    assert process_year_end(2027) == 3
    new_el = LeaveBalance.objects.get(
        employee_id=faculty, category="EL", year=2027,
    )
    assert new_el.carried_in == Decimal("5")
    assert new_el.converted_in == Decimal("3.75")
    assert new_el.remaining == Decimal("8.75")
    old_vl = LeaveBalance.objects.get(
        employee_id=faculty, category="VL", year=2026,
    )
    assert old_vl.remaining == 0
    assert process_year_end(2027) == 0
    assert LeaveYearEndRun.objects.filter(employee_id=faculty, year=2027).exists()


def test_sla_reminder_only_while_task_is_pending(stub_iam, people):
    _hierarchy(people)
    application = LeaveApplication.objects.create(
        employee_id=people["employee"], employee_kind="faculty",
        department="Engineering", category="CL", status="unit_head_review",
        start_date=date(2026, 12, 7), end_date=date(2026, 12, 7),
        reason="Personal", assigned_user_id=people["unit_head"],
        assigned_role="unit_head",
        assigned_at=timezone.now() - timedelta(hours=2),
    )
    LeaveSLAConfig.objects.create(
        request_type="leave", reminder_after_hours=1, escalation_after_hours=4,
    )
    now = timezone.now()
    result = process_sla_thresholds(now)
    assert result == {"reminders": 1, "escalations": 0}
    application.status = "approved"
    application.save()
    later = process_sla_thresholds(now + timedelta(hours=10))
    assert later == {"reminders": 0, "escalations": 0}
