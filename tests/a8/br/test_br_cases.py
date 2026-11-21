from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from functools import partial
from pathlib import Path

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory.models import UserRef as DirectoryUser
from modules.mms.models import (
    Announcement,
    Enrollment,
    Feedback,
    MenuEntry,
    MenuWeek,
    MonthlyBill,
    NotificationOutbox,
    RebateRequest,
    RegistrationWindow,
    RequestHistory,
    RoleAssignment,
    SpecialFoodHistory,
    SpecialFoodRequest,
    StudentRequest,
    VacationResponse,
    VacationSurvey,
)

pytestmark = pytest.mark.django_db

DESIGN_PATH = Path(__file__).resolve().parents[3] / "a8_design" / "BR_DESIGN.json"
DESIGN = json.loads(DESIGN_PATH.read_text())["design"]
CASES = DESIGN["test_cases"]
BLOCKED = {
    case["id"]: case["blocked_reason"]
    for case in CASES
    if case["status"] == "BLOCKED"
}

PERMISSIONS = {
    "student": ("mess_management.student.use",),
    "admin": ("mess_management.roles.manage",),
    "caretaker": (
        "mess_management.operations.view",
        "mess_management.operations.manage",
        "mess_management.requests.review",
        "mess_management.menu.manage",
        "mess_management.billing.manage",
        "mess_management.feedback.view",
        "mess_management.surveys.manage",
        "mess_management.announcements.publish",
        "mess_management.reports.caretaker",
    ),
    "warden": (
        "mess_management.operations.view",
        "mess_management.feedback.view",
        "mess_management.announcements.publish",
        "mess_management.reports.warden",
    ),
}


class BRFixture:
    def __init__(self, install_iam, user_ref):
        self.install_iam = install_iam
        self.make_user_ref = user_ref
        self.identities = {}

    def identity(self, user_id, kind="student", *, active=True):
        row, _ = DirectoryUser.objects.get_or_create(
            user_id=user_id,
            defaults={
                "username": f"br-{user_id}",
                "display_name": f"BR user {user_id}",
                "kind": kind,
                "is_active": active,
            },
        )
        if row.kind != kind or row.is_active != active:
            row.kind = kind
            row.is_active = active
            row.save(update_fields=["kind", "is_active"])
        if kind in {"faculty", "staff"}:
            self.identities[user_id] = self.make_user_ref(
                user_id, name=row.display_name, kind=kind)
        return row

    def client(self, user_id, role="student", *, permissions=None, module=True):
        self.install_iam(
            make_session(
                user_id=user_id,
                kind="student" if role == "student" else "staff",
                roles=(role,),
                active_role=role,
                modules=("mess_management",) if module else (),
                permissions=PERMISSIONS[role] if permissions is None else permissions,
            ),
            users=self.identities,
        )
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token br-test")
        return client

    def assignment(self, user_id, role, *, start=None, end=None, current=True):
        now = timezone.now()
        self.identity(user_id, "faculty")
        return RoleAssignment.objects.create(
            role=role,
            user_id=user_id,
            starts_at=start or now - timedelta(days=1),
            ends_at=end or now + timedelta(days=30),
            is_current=current,
            assigned_by_user_id=9000,
        )

    def registered_student(self, user_id, *, deregistered_at=None, registered_at=None):
        self.identity(user_id, "student")
        return Enrollment.objects.create(
            user_id=user_id,
            registered_at=registered_at or timezone.now() - timedelta(days=60),
            deregistered_at=deregistered_at,
        )

    def window(self, *, opens=None, closes=None, cycle="BR-cycle"):
        now = timezone.now()
        return RegistrationWindow.objects.create(
            cycle=cycle,
            opens_at=opens or now - timedelta(days=1),
            closes_at=closes or now + timedelta(days=1),
            opened_by_user_id=3001,
        )

    def request(self, user_id=1001, kind="registration", *, status="pending", window=None):
        row = StudentRequest.objects.create(
            user_id=user_id, kind=kind, status=status, window=window)
        RequestHistory.objects.create(
            request=row, status=status, actor_user_id=user_id)
        return row

    def actor(self, user_id, role):
        from fusion_auth.principal import Principal

        return Principal.from_session(
            make_session(
                user_id=user_id,
                kind="staff",
                roles=(role,),
                active_role=role,
                modules=("mess_management",),
                permissions=PERMISSIONS[role],
            )
        )


def _week_entries(item="Meal"):
    return [
        {"day": day, "meal": meal, "item": item}
        for day in range(7)
        for meal in ("breakfast", "lunch", "dinner")
    ]


def _published_menu(*, week_start=None, item="Meal", user_id=3001):
    day = timezone.localdate()
    start = week_start or day + timedelta(days=(7 - day.weekday()) % 7)
    week = MenuWeek.objects.create(
        week_start=start, published_at=timezone.now(), updated_by_user_id=user_id)
    MenuEntry.objects.bulk_create(
        MenuEntry(week=week, day=entry["day"], meal=entry["meal"], item=item)
        for entry in _week_entries(item)
    )
    return week


def _rebate_dates(offset=3, duration=3):
    start = timezone.localdate() + timedelta(days=offset)
    return start, start + timedelta(days=duration - 1)


def _submit_rebate(client, *, reason="medical", explanation="", starts=None, ends=None):
    if starts is None or ends is None:
        starts, ends = _rebate_dates()
    payload = {
        "explanation": explanation,
        "starts_on": starts.isoformat(),
        "ends_on": ends.isoformat(),
    }
    if reason is not None:
        payload["reason"] = reason
    return client.post("/api/v1/mms/rebates", payload, format="json")


def _decide_request(client, request, approved):
    return client.post(
        f"/api/v1/mms/requests/{request.pk}/decision",
        {"approve": approved},
        format="json",
    )


def _submit_registration(client, window):
    return client.post(
        "/api/v1/mms/requests",
        {"kind": "registration", "window_id": window.pk},
        format="json",
    )


def _submit_deregistration(client):
    return client.post(
        "/api/v1/mms/requests", {"kind": "deregistration"}, format="json")


def _create_survey(*, deadline=None):
    today = timezone.localdate()
    return VacationSurvey.objects.create(
        title="BR survey",
        vacation_starts_on=today + timedelta(days=20),
        vacation_ends_on=today + timedelta(days=27),
        deadline=deadline or timezone.now() + timedelta(days=5),
        created_by_user_id=3001,
    )


def _food(user_id=1001, *, state="approved", requested_for=None, charge="12.50"):
    request = SpecialFoodRequest.objects.create(
        user_id=user_id,
        reason="illness",
        details="BR food case",
        requested_for=requested_for or (timezone.localdate() + timedelta(days=1)),
        status=state,
        charge_amount=Decimal(charge) if charge is not None else None,
    )
    SpecialFoodHistory.objects.create(request=request, status=state, actor_user_id=user_id)
    return request


def _bill_for(user_id, *, year=2026, month=12, status="generated", total="1.00"):
    return MonthlyBill.objects.create(
        user_id=user_id,
        year=year,
        month=month,
        daily_rate=Decimal("10.00"),
        served_days=1,
        special_food_charges=Decimal("0.00"),
        rebate_deduction=Decimal("0.00"),
        total=Decimal(total),
        status=status,
    )


def _assert_request_notification(topic, user_id):
    assert NotificationOutbox.objects.filter(
        topic=topic, recipient_user_id=user_id).exists()


def _case_002(h):
    h.identity(4101, "faculty")
    h.assignment(4101, "caretaker")
    result = h.client(9000, "admin").post(
        "/api/v1/mms/roles",
        {"role": "caretaker", "user_id": 4101,
         "ends_at": (timezone.now() + timedelta(days=21)).isoformat()},
        format="json",
    )
    assert result.status_code == 201
    assert result.json()["user_id"] == 4101


def _case_003(h):
    h.identity(4101, "faculty")
    h.assignment(4101, "caretaker")
    before = RoleAssignment.objects.get(role="caretaker", is_current=True)
    h.identity(4102, "faculty")
    result = h.client(9000, "admin").post(
        "/api/v1/mms/roles",
        {"role": "caretaker", "user_id": 4102,
         "ends_at": (timezone.now() + timedelta(days=21)).isoformat()},
        format="json",
    )
    assert result.status_code == 201
    assert RoleAssignment.objects.filter(role="caretaker", is_current=True).count() == 1
    before.refresh_from_db()
    assert before.is_current is False


def _case_005(h):
    h.identity(4101, "faculty")
    old = h.assignment(4101, "caretaker")
    h.identity(4102, "faculty")
    h.assignment(4201, "warden")
    response = h.client(9000, "admin").post(
        "/api/v1/mms/roles",
        {"role": "caretaker", "user_id": 4102,
         "ends_at": (timezone.now() + timedelta(days=30)).isoformat()},
        format="json",
    )
    assert response.status_code == 201
    old.refresh_from_db()
    assert old.is_current is False
    assert RoleAssignment.objects.filter(role="caretaker", is_current=True).count() == 1


def _case_006(h):
    h.identity(4201, "faculty")
    old = h.assignment(4201, "warden")
    h.identity(4202, "faculty")
    response = h.client(9000, "admin").post(
        "/api/v1/mms/roles",
        {"role": "warden", "user_id": 4202,
         "ends_at": (timezone.now() + timedelta(days=30)).isoformat()},
        format="json",
    )
    assert response.status_code == 201
    old.refresh_from_db()
    assert old.is_current is False
    assert RoleAssignment.objects.filter(role="warden", is_current=True).count() == 1


def _case_007(h):
    h.request()
    response = h.client(9000, "admin").get("/api/v1/mms/requests")
    assert response.status_code == 403
    assert StudentRequest.objects.count() == 1


def _case_008(h):
    _bill_for(1001)
    Feedback.objects.create(user_id=1001, message="Stored")
    bills = h.client(9000, "admin").get("/api/v1/mms/bills")
    feedback = h.client(9000, "admin").get("/api/v1/mms/feedback")
    assert bills.status_code == 403
    assert feedback.status_code == 403
    assert MonthlyBill.objects.count() == 1
    assert Feedback.objects.count() == 1


def _case_009(h, role):
    old_user, new_user = (4101, 4102) if role == "caretaker" else (4201, 4202)
    h.identity(old_user, "faculty")
    before = h.assignment(old_user, role)
    h.identity(new_user, "faculty")
    recorded_time = timezone.now()
    response = h.client(9000, "admin").post(
        "/api/v1/mms/roles",
        {"role": role, "user_id": new_user,
         "ends_at": (recorded_time + timedelta(days=30)).isoformat()},
        format="json",
    )
    assert response.status_code == 201
    before.refresh_from_db()
    assert before.ends_at <= recorded_time + timedelta(seconds=1)
    assert RoleAssignment.objects.filter(
        user_id=new_user, role=role, is_current=True,
        starts_at__lte=timezone.now(), ends_at__gt=timezone.now()).exists()


def _case_011(h):
    h.identity(4101, "faculty")
    h.assignment(4101, "caretaker")
    window = h.window()
    request = h.request(user_id=1001, kind="registration", window=window)
    h.identity(4102, "faculty")
    h.client(9000, "admin").post(
        "/api/v1/mms/roles",
        {"role": "caretaker", "user_id": 4102,
         "ends_at": (timezone.now() + timedelta(days=20)).isoformat()},
        format="json",
    )
    client = h.client(4102, "caretaker")
    listing = client.get("/api/v1/mms/requests")
    assert listing.status_code == 200
    assert any(row["id"] == request.pk for row in listing.json()["results"])
    decision = _decide_request(client, request, True)
    assert decision.status_code == 200
    request.refresh_from_db()
    assert request.status == "approved"


def _case_012(h):
    h.assignment(3001, "caretaker")
    now = timezone.now()
    response = h.client(3001, "caretaker").post(
        "/api/v1/mms/registration-windows",
        {"cycle": "BR window", "opens_at": (now - timedelta(minutes=1)).isoformat(),
         "closes_at": (now + timedelta(days=1)).isoformat()},
        format="json",
    )
    assert response.status_code == 201
    assert RegistrationWindow.objects.get(cycle="BR window").opened_by_user_id == 3001


def _case_013(h):
    response = h.client(3002, "warden").post(
        "/api/v1/mms/registration-windows",
        {"cycle": "Denied", "opens_at": timezone.now().isoformat(),
         "closes_at": (timezone.now() + timedelta(days=1)).isoformat()},
        format="json",
    )
    assert response.status_code == 403
    assert not RegistrationWindow.objects.exists()


def _case_014(h):
    window = h.window()
    response = _submit_registration(h.client(1001), window)
    assert response.status_code == 201
    assert response.json()["status"] == "pending"


def _case_015(h):
    window = h.window(opens=timezone.now() - timedelta(days=2),
                      closes=timezone.now() - timedelta(days=1))
    response = _submit_registration(h.client(1001), window)
    assert response.status_code == 409
    assert not StudentRequest.objects.exists()


def _case_016_017(h, kind, approve):
    h.assignment(3001, "caretaker")
    window = h.window() if kind == "registration" else None
    request = h.request(user_id=1001, kind=kind, window=window)
    response = _decide_request(h.client(3001, "caretaker"), request, approve)
    assert response.status_code == 200
    assert response.json()["status"] == ("approved" if approve else "rejected")


def _case_018(h):
    h.assignment(3002, "warden")
    before = h.request(user_id=1001, kind="registration", window=h.window())
    response = _decide_request(h.client(3002, "warden"), before, True)
    assert response.status_code == 403
    before.refresh_from_db()
    assert before.status == "pending"
    assert list(before.history.values_list("status", flat=True)) == ["pending"]


def _case_019(h):
    h.assignment(3002, "warden")
    registration = h.request(user_id=1001, window=h.window())
    deregistration = h.request(user_id=1002, kind="deregistration")
    response = h.client(3002, "warden").get("/api/v1/mms/requests")
    assert response.status_code == 200
    ids = {row["id"] for row in response.json()["results"]}
    assert {registration.pk, deregistration.pk} <= ids
    assert all("decision" not in row for row in response.json()["results"])


def _case_020(h):
    h.registered_student(1001)
    response = _submit_deregistration(h.client(1001))
    assert response.status_code == 201
    assert response.json()["status"] == "pending"


def _case_021(h):
    response = _submit_deregistration(h.client(1001))
    assert response.status_code == 409
    assert not StudentRequest.objects.exists()


def _case_022(h):
    from modules.mms.services.operations import activate_deregistrations

    h.assignment(3001, "caretaker")
    enrollment = h.registered_student(1001)
    request = h.request(user_id=1001, kind="deregistration")
    approved = _decide_request(h.client(3001, "caretaker"), request, True)
    assert approved.status_code == 200
    request.refresh_from_db()
    effective_at = request.effective_at
    assert timezone.localdate(effective_at) == (
        timezone.localdate(request.decided_at) + timedelta(days=1))
    enrollment.refresh_from_db()
    assert enrollment.deregistered_at is None
    assert activate_deregistrations(now=effective_at) == 1
    enrollment.refresh_from_db()
    assert enrollment.deregistered_at == effective_at


def _case_023_024(h, valid):
    h.assignment(3001, "caretaker")
    week_start = timezone.localdate() + timedelta(days=(7 - timezone.localdate().weekday()) % 7)
    entries = _week_entries()
    if not valid:
        entries.pop()
    response = h.client(3001, "caretaker").post(
        "/api/v1/mms/menu",
        {"week_start": week_start.isoformat(), "entries": entries},
        format="json",
    )
    if valid:
        assert response.status_code == 201
        row = MenuWeek.objects.get(week_start=week_start)
        pairs = set(row.entries.values_list("day", "meal"))
        assert pairs == {(d, m) for d in range(7) for m in ("breakfast", "lunch", "dinner")}
    else:
        assert response.status_code == 409
        assert not MenuWeek.objects.filter(week_start=week_start).exists()


def _case_025(h):
    h.identity(1001, "student")
    h.assignment(3001, "caretaker")
    response = h.client(3001, "caretaker").post(
        "/api/v1/mms/menu",
        {"week_start": "2026-12-07", "entries": _week_entries("Published")},
        format="json",
    )
    assert response.status_code == 201
    assert NotificationOutbox.objects.filter(
        topic="menu.updated", recipient_user_id=1001).exists()


def _case_026(h):
    h.assignment(3001, "caretaker")
    week = _published_menu(item="Stable")
    response = h.client(3001, "caretaker").post(
        "/api/v1/mms/menu",
        {"week_start": week.week_start.isoformat(), "entries": _week_entries("Broken")[:-1]},
        format="json",
    )
    assert response.status_code == 409
    week.refresh_from_db()
    assert week.entries.count() == 21
    assert not week.entries.filter(item="Broken").exists()
    assert not NotificationOutbox.objects.exists()


def _case_027(h):
    from modules.mms.services.operations import generate_bills

    user_id, year, month = 1001, 2026, 12
    starts = timezone.make_aware(datetime(year, month, 1))
    h.registered_student(user_id, registered_at=starts)
    bills = generate_bills(
        system_event=True, year=year, month=month,
        inputs=[{"user_id": user_id, "daily_rate": "1.25", "served_days": 10}],
    )
    assert len(bills) == 1
    assert (bills[0].year, bills[0].month) == (year, month)
    assert bills[0].total == Decimal("12.50")


def _case_028(h):
    from modules.mms.services.operations import generate_bills

    year, month, user_id = 2026, 12, 1001
    starts = timezone.make_aware(datetime(year, month, 1))
    h.registered_student(user_id, registered_at=starts)
    begin = date(year, month, 4)
    RebateRequest.objects.create(
        user_id=user_id, reason="medical", starts_on=begin,
        ends_on=begin + timedelta(days=2), status="approved")
    _food(user_id, requested_for=date(year, month, 5), charge="15.00")
    bill = generate_bills(
        system_event=True, year=year, month=month,
        inputs=[{"user_id": user_id, "daily_rate": "10", "served_days": 20}],
    )[0]
    assert bill.total == Decimal("185.00")
    assert bill.special_food_charges == Decimal("15.00")
    assert bill.rebate_deduction == Decimal("30.00")


def _case_029(h):
    h.assignment(3001, "caretaker")
    bill = _bill_for(1001, status="generated")
    early = h.client(3001, "caretaker").post(
        f"/api/v1/mms/bills/{bill.pk}/publish", {}, format="json")
    assert early.status_code == 409
    assert h.client(1001).get("/api/v1/mms/bills").json()["results"] == []
    caretaker = h.client(3001, "caretaker")
    finalized = caretaker.post(f"/api/v1/mms/bills/{bill.pk}/finalize", {}, format="json")
    assert finalized.status_code == 200
    published = caretaker.post(f"/api/v1/mms/bills/{bill.pk}/publish", {}, format="json")
    assert published.status_code == 200
    assert len(h.client(1001).get("/api/v1/mms/bills").json()["results"]) == 1


def _case_030_031(h, status, expected_deduction):
    from modules.mms.services.operations import generate_bills

    year, month, user_id = 2026, 12, 1001
    starts = timezone.make_aware(datetime(year, month, 1))
    h.registered_student(user_id, registered_at=starts)
    rebate_start = date(year, month, 5)
    RebateRequest.objects.create(
        user_id=user_id, reason="medical", starts_on=rebate_start,
        ends_on=rebate_start + timedelta(days=2), status=status)
    bill = generate_bills(
        system_event=True, year=year, month=month,
        inputs=[{"user_id": user_id, "daily_rate": "10", "served_days": 20}],
    )[0]
    assert bill.rebate_deduction == Decimal(expected_deduction)


def _case_032_033(h, role):
    h.assignment(3001, role)
    feedback = Feedback.objects.create(user_id=1001, message="Student text")
    response = h.client(3001, role).get("/api/v1/mms/feedback")
    assert response.status_code == 200
    assert response.json()["results"][0]["id"] == feedback.pk
    assert response.json()["results"][0]["message"] == "Student text"


def _case_034_035(h, days):
    h.registered_student(1001)
    start = timezone.localdate() + timedelta(days=2)
    end = start + timedelta(days=days - 1)
    response = _submit_rebate(h.client(1001), starts=start, ends=end)
    if days == 3:
        assert response.status_code == 201
    else:
        assert response.status_code == 409
        assert not RebateRequest.objects.exists()


def _case_036_037(h, lead_days):
    h.registered_student(1001)
    start = timezone.localdate() + timedelta(days=lead_days)
    response = _submit_rebate(
        h.client(1001), starts=start, ends=start + timedelta(days=2))
    if lead_days >= 1:
        assert response.status_code == 201
    else:
        assert response.status_code == 409
        assert not RebateRequest.objects.exists()


def _case_038_039(h, overlap):
    h.registered_student(1001)
    start, end = _rebate_dates()
    RebateRequest.objects.create(
        user_id=1001, reason="medical", starts_on=start,
        ends_on=end, status="pending")
    if overlap:
        new_start = end
        new_end = end + timedelta(days=2)
    else:
        new_start = end + timedelta(days=1)
        new_end = new_start + timedelta(days=2)
    result = _submit_rebate(h.client(1001), starts=new_start, ends=new_end)
    if overlap:
        assert result.status_code == 409
        assert RebateRequest.objects.count() == 1
    else:
        assert result.status_code == 201
        assert RebateRequest.objects.count() == 2


def _case_040_041(h, valid):
    reason_cases = (
        [
            ("medical", ""),
            ("institute_leave", ""),
            ("family_function", ""),
            ("other", "Other reason detail"),
        ]
        if valid
        else [
            (None, ""),
            ("unsupported", ""),
            ("other", ""),
        ]
    )
    for offset, (reason, explanation) in enumerate(reason_cases, start=1):
        user_id = 1000 + offset
        h.registered_student(user_id)
        starts = timezone.localdate() + timedelta(days=offset + 2)
        response = _submit_rebate(
            h.client(user_id), reason=reason, explanation=explanation,
            starts=starts, ends=starts + timedelta(days=2))
        if valid:
            assert response.status_code == 201
            assert response.json()["reason"] == reason
            assert response.json()["explanation"] == explanation
        else:
            assert response.status_code == 409
            assert not RebateRequest.objects.filter(user_id=user_id).exists()


def _case_042(h):
    from modules.mms.services.operations import generate_bills

    year, month, user_id = 2026, 12, 1001
    h.registered_student(
        user_id, registered_at=timezone.make_aware(datetime(year, month, 1)))
    start = date(year, month, 4)
    rebate = RebateRequest.objects.create(
        user_id=user_id, reason="medical", starts_on=start,
        ends_on=start + timedelta(days=2), status="approved")
    response = h.client(1001).get("/api/v1/mms/rebates")
    assert response.status_code == 200
    assert response.json()["results"][0]["starts_on"] == rebate.starts_on.isoformat()
    bill = generate_bills(
        system_event=True, year=year, month=month,
        inputs=[{"user_id": user_id, "daily_rate": "10", "served_days": 20}],
    )[0]
    assert bill.rebate_deduction == Decimal("30.00")


def _case_044(h):
    h.assignment(3001, "caretaker")
    included = h.registered_student(1001)
    excluded = h.registered_student(
        1002, deregistered_at=timezone.now() - timedelta(days=1))
    response = h.client(3001, "caretaker").post(
        "/api/v1/mms/vacation-surveys",
        {
            "title": "Upcoming vacation",
            "vacation_starts_on": (timezone.localdate() + timedelta(days=20)).isoformat(),
            "vacation_ends_on": (timezone.localdate() + timedelta(days=27)).isoformat(),
            "deadline": (timezone.now() + timedelta(days=7)).isoformat(),
        },
        format="json",
    )
    assert response.status_code == 201
    recipients = set(NotificationOutbox.objects.filter(
        topic="vacation.created").values_list("recipient_user_id", flat=True))
    assert included.user_id in recipients
    assert excluded.user_id not in recipients


def _case_045_046(h, explicit):
    from modules.mms.services.operations import default_vacation_responses

    student = h.registered_student(1001)
    deadline = timezone.now() - timedelta(seconds=1)
    survey = _create_survey(deadline=deadline)
    if explicit:
        VacationResponse.objects.create(
            survey=survey, user_id=student.user_id, response="yes")
    assert default_vacation_responses(now=timezone.now()) == (0 if explicit else 1)
    row = VacationResponse.objects.get(survey=survey, user_id=student.user_id)
    assert row.response == ("yes" if explicit else "no")
    assert row.is_default is (not explicit)


def _case_048_049(h, lead_days):
    requested_for = timezone.localdate() + timedelta(days=lead_days)
    response = h.client(1001).post(
        "/api/v1/mms/special-food",
        {"reason": "illness", "details": "BR request",
         "requested_for": requested_for.isoformat()},
        format="json",
    )
    if lead_days >= 1:
        assert response.status_code == 201
        assert response.json()["status"] == "requested"
    else:
        assert response.status_code == 409
        assert not SpecialFoodRequest.objects.exists()


def _case_051(h):
    from modules.mms.services.operations import generate_bills

    year, month, user_id = 2026, 12, 1001
    h.registered_student(
        user_id, registered_at=timezone.make_aware(datetime(year, month, 1)))
    _food(user_id, requested_for=date(year, month, 10), charge="8.75")
    bill = generate_bills(
        system_event=True, year=year, month=month,
        inputs=[{"user_id": user_id, "daily_rate": "10", "served_days": 20}],
    )[0]
    assert bill.special_food_charges == Decimal("8.75")
    assert bill.total == Decimal("208.75")


def _case_053(h):
    h.assignment(3001, "caretaker")
    request = _food(state="requested", charge=None)
    response = h.client(3001, "caretaker").post(
        f"/api/v1/mms/special-food/{request.pk}/decision",
        {"approve": False}, format="json")
    assert response.status_code == 200
    request.refresh_from_db()
    assert request.status == "rejected"


def _case_055_056(h, role):
    h.assignment(3001, role)
    h.identity(1001, "student")
    result = h.client(3001, role).post(
        "/api/v1/mms/announcements",
        {"title": "Mess notice", "body": "Schedule update"}, format="json")
    assert result.status_code == 201
    assert Announcement.objects.filter(pk=result.json()["id"]).exists()
    assert NotificationOutbox.objects.filter(
        topic="announcement.published", recipient_user_id=1001).exists()


def _case_057(h):
    h.assignment(3001, "caretaker")
    result = h.client(1001, "student").post(
        "/api/v1/mms/announcements",
        {"title": "Unauthorized", "body": "No publication"}, format="json")
    assert result.status_code == 403
    assert not Announcement.objects.exists()
    assert not NotificationOutbox.objects.exists()


def _case_058(h):
    published = Announcement.objects.create(
        title="BR notice", body="History item", published_by_user_id=3001,
        published_by_role="caretaker", published_at=timezone.now())
    h.identity(1001, "student")
    h.assignment(3001, "caretaker")
    h.assignment(3002, "warden")
    for user_id, role in ((1001, "student"), (3001, "caretaker"), (3002, "warden")):
        response = h.client(user_id, role).get("/api/v1/mms/announcements")
        assert response.status_code == 200
        assert response.json()["results"][0]["id"] == published.pk


def _case_060_061_062_063(h, actor_role, reports):
    if actor_role == "warden":
        h.assignment(3002, "warden")
        actor_id = 3002
    elif actor_role == "caretaker":
        h.assignment(3001, "caretaker")
        actor_id = 3001
    for report in reports:
        response = h.client(actor_id, actor_role).get(
            f"/api/v1/mms/reports?type={report}")
        allowed = (
            actor_role == "warden" and report in {"registered", "rebates", "vacation"}
        ) or (
            actor_role == "caretaker" and report in {
                "registration_trends", "special_meals", "billing_summary"}
        )
        if allowed:
            assert response.status_code == 200
            assert isinstance(response.json()["results"], list)
        else:
            assert response.status_code == 403
            assert "results" not in response.json()


def _case_064(h):
    window = h.window()
    opened = _submit_registration(h.client(1001), window)
    assert opened.status_code == 201
    _assert_request_notification("request.submitted", 1001)
    h.assignment(3001, "caretaker")
    caretaker = h.client(3001, "caretaker")
    registration = StudentRequest.objects.get(pk=opened.json()["id"])
    decision = _decide_request(caretaker, registration, True)
    assert decision.status_code == 200
    _assert_request_notification("request.decided", 1001)

    h.registered_student(1002)
    deregistration = _submit_deregistration(h.client(1002))
    assert deregistration.status_code == 201
    _assert_request_notification("request.submitted", 1002)
    caretaker = h.client(3001, "caretaker")
    decision = _decide_request(
        caretaker, StudentRequest.objects.get(pk=deregistration.json()["id"]), False)
    assert decision.status_code == 200
    _assert_request_notification("request.decided", 1002)


def _case_065(h):
    h.registered_student(1001)
    response = _submit_deregistration(h.client(1001))
    assert response.status_code == 201
    _assert_request_notification("request.submitted", 1001)


def _case_066(h):
    h.assignment(3001, "caretaker")
    request_result = h.client(1001).post(
        "/api/v1/mms/special-food",
        {
            "reason": "illness",
            "details": "BR notification case",
            "requested_for": (timezone.localdate() + timedelta(days=1)).isoformat(),
        },
        format="json",
    )
    assert request_result.status_code == 201
    _assert_request_notification("special_food.submitted", 1001)
    decision = h.client(3001, "caretaker").post(
        f"/api/v1/mms/special-food/{request_result.json()['id']}/decision",
        {"approve": False}, format="json")
    assert decision.status_code == 200
    _assert_request_notification("special_food.decided", 1001)


def _case_067(h):
    h.assignment(3001, "caretaker")
    h.registered_student(1001)
    h.registered_student(1002)
    from modules.mms.services.operations import create_vacation_survey, send_vacation_reminder

    created = create_vacation_survey(
        actor=h.actor(3001, "caretaker"), title="BR survey",
        starts_on=timezone.localdate() + timedelta(days=20),
        ends_on=timezone.localdate() + timedelta(days=27),
        deadline=timezone.now() + timedelta(days=5))
    assert NotificationOutbox.objects.filter(
        topic="vacation.created", recipient_user_id=1001).exists()
    VacationResponse.objects.create(survey=created, user_id=1001, response="yes")
    assert send_vacation_reminder(
        actor=h.actor(3001, "caretaker"), survey_id=created.pk) == 1
    _assert_request_notification("vacation.reminder", 1002)


def _case_068(h):
    h.assignment(3001, "caretaker")
    h.identity(1001, "student")
    current_week = _published_menu(user_id=3001)
    menu_update = h.client(3001, "caretaker").post(
        "/api/v1/mms/menu",
        {"week_start": current_week.week_start.isoformat(),
         "entries": _week_entries("Updated")},
        format="json",
    )
    assert menu_update.status_code == 201
    bill = _bill_for(1001)
    finalized = h.client(3001, "caretaker").post(
        f"/api/v1/mms/bills/{bill.pk}/finalize", {}, format="json")
    assert finalized.status_code == 200
    published = h.client(3001, "caretaker").post(
        f"/api/v1/mms/bills/{bill.pk}/publish", {}, format="json")
    assert published.status_code == 200
    announcement = h.client(3001, "caretaker").post(
        "/api/v1/mms/announcements",
        {"title": "Notice", "body": "Update"}, format="json")
    assert announcement.status_code == 201
    topics = set(NotificationOutbox.objects.values_list("topic", flat=True))
    assert {"menu.updated", "bill.published", "announcement.published"} <= topics


def _case_071_072_073(h, role):
    if role == "caretaker":
        h.assignment(3001, role)
    elif role == "warden":
        h.assignment(3002, role)
    _published_menu()
    response = h.client(
        1001 if role == "student" else (3001 if role == "caretaker" else 3002),
        role,
    ).get("/api/v1/mms/menu")
    assert response.status_code == 200
    assert len(response.json()["results"]) == 1


def _case_075_076(h, role):
    if role == "caretaker":
        h.assignment(3001, role)
        client = h.client(3001, role)
        week = _published_menu(item="Existing")
        for operation in ("add", "modify", "delete"):
            if operation == "add":
                start = week.week_start + timedelta(days=7)
                response = client.post(
                    "/api/v1/mms/menu",
                    {"week_start": start.isoformat(), "entries": _week_entries("Added")},
                    format="json",
                )
                assert response.status_code == 201
                assert MenuWeek.objects.get(week_start=start).entries.filter(
                    item="Added").count() == 21
            elif operation == "modify":
                response = client.post(
                    "/api/v1/mms/menu",
                    {"week_start": week.week_start.isoformat(),
                     "entries": _week_entries("Changed")},
                    format="json",
                )
                assert response.status_code == 201
                week.refresh_from_db()
                assert week.entries.filter(item="Changed").count() == 21
            else:
                entries = _week_entries("Changed")
                entries.pop()
                response = client.post(
                    "/api/v1/mms/menu",
                    {"week_start": week.week_start.isoformat(), "entries": entries},
                    format="json",
                )
                assert response.status_code == 201
                week.refresh_from_db()
                assert week.entries.count() == 20
    else:
        week = _published_menu(item="Existing")
        for actor_role in ("student", "warden", "admin"):
            actor_id = {"student": 1001, "warden": 3002, "admin": 9000}[actor_role]
            client = h.client(actor_id, actor_role)
            for operation in ("add", "modify", "delete"):
                entries = _week_entries("Changed")
                week_start = week.week_start
                if operation == "add":
                    week_start += timedelta(days=7)
                elif operation == "delete":
                    entries.pop()
                response = client.post(
                    "/api/v1/mms/menu",
                    {"week_start": week_start.isoformat(), "entries": entries},
                    format="json",
                )
                assert response.status_code == 403
                week.refresh_from_db()
                assert week.entries.filter(item="Existing").count() == 21
                assert not week.entries.filter(item="Changed").exists()


def _case_077(h):
    _bill_for(1001, status="published", total="27.25")
    _bill_for(2002, status="published", total="99.99")
    response = h.client(1001).get("/api/v1/mms/bills")
    assert response.status_code == 200
    assert {row["user_id"] for row in response.json()["results"]} == {1001}
    assert Decimal(str(response.json()["balance"])) == Decimal("27.25")


def _case_080_081(h, answer):
    h.registered_student(1001)
    survey = _create_survey()
    response = h.client(1001).post(
        f"/api/v1/mms/vacation-surveys/{survey.pk}/responses",
        {"response": answer.lower()}, format="json")
    assert response.status_code == 200
    assert VacationResponse.objects.get(survey=survey, user_id=1001).response == answer.lower()


def _case_082(h):
    h.registered_student(1001)
    survey = _create_survey()
    response = h.client(1001).post(
        f"/api/v1/mms/vacation-surveys/{survey.pk}/responses",
        {"response": "Maybe"}, format="json")
    assert response.status_code == 409
    assert not VacationResponse.objects.exists()


def _case_083_084(h, own):
    own_id = 1001
    other_id = 2002
    request = h.request(user_id=own_id, kind="registration",
                        window=h.window())
    actor_id = own_id if own else other_id
    response = h.client(actor_id).get("/api/v1/mms/requests")
    assert response.status_code == 200
    returned = response.json()["results"]
    if own:
        assert len(returned) == 1
        assert returned[0]["id"] == request.pk
        assert returned[0]["history"]
    else:
        assert all(row["user_id"] == other_id for row in returned)
        assert request.pk not in {row["id"] for row in returned}


HANDLERS = {
    "TC-BR-002": _case_002,
    "TC-BR-003": _case_003,
    "TC-BR-005": _case_005,
    "TC-BR-006": _case_006,
    "TC-BR-007": _case_007,
    "TC-BR-008": _case_008,
    "TC-BR-009": partial(_case_009, role="caretaker"),
    "TC-BR-010": partial(_case_009, role="warden"),
    "TC-BR-011": _case_011,
    "TC-BR-012": _case_012,
    "TC-BR-013": _case_013,
    "TC-BR-014": _case_014,
    "TC-BR-015": _case_015,
    "TC-BR-016": partial(_case_016_017, kind="registration", approve=True),
    "TC-BR-017": partial(_case_016_017, kind="deregistration", approve=False),
    "TC-BR-018": _case_018,
    "TC-BR-019": _case_019,
    "TC-BR-020": _case_020,
    "TC-BR-021": _case_021,
    "TC-BR-022": _case_022,
    "TC-BR-023": partial(_case_023_024, valid=True),
    "TC-BR-024": partial(_case_023_024, valid=False),
    "TC-BR-025": _case_025,
    "TC-BR-026": _case_026,
    "TC-BR-027": _case_027,
    "TC-BR-028": _case_028,
    "TC-BR-029": _case_029,
    "TC-BR-030": partial(_case_030_031, status="approved", expected_deduction="30.00"),
    "TC-BR-031": partial(_case_030_031, status="pending", expected_deduction="0.00"),
    "TC-BR-032": partial(_case_032_033, role="caretaker"),
    "TC-BR-033": partial(_case_032_033, role="warden"),
    "TC-BR-034": partial(_case_034_035, days=2),
    "TC-BR-035": partial(_case_034_035, days=3),
    "TC-BR-036": partial(_case_036_037, lead_days=1),
    "TC-BR-037": partial(_case_036_037, lead_days=0),
    "TC-BR-038": partial(_case_038_039, overlap=True),
    "TC-BR-039": partial(_case_038_039, overlap=False),
    "TC-BR-040": partial(_case_040_041, valid=True),
    "TC-BR-041": partial(_case_040_041, valid=False),
    "TC-BR-042": _case_042,
    "TC-BR-044": _case_044,
    "TC-BR-045": partial(_case_045_046, explicit=False),
    "TC-BR-046": partial(_case_045_046, explicit=True),
    "TC-BR-048": partial(_case_048_049, lead_days=1),
    "TC-BR-049": partial(_case_048_049, lead_days=0),
    "TC-BR-051": _case_051,
    "TC-BR-053": _case_053,
    "TC-BR-055": partial(_case_055_056, role="caretaker"),
    "TC-BR-056": partial(_case_055_056, role="warden"),
    "TC-BR-057": _case_057,
    "TC-BR-058": _case_058,
    "TC-BR-060": partial(
        _case_060_061_062_063, actor_role="warden",
        reports=("registered", "rebates", "vacation")),
    "TC-BR-061": partial(
        _case_060_061_062_063, actor_role="caretaker", reports=("registered",)),
    "TC-BR-062": partial(
        _case_060_061_062_063, actor_role="caretaker",
        reports=("registration_trends", "special_meals", "billing_summary")),
    "TC-BR-063": partial(
        _case_060_061_062_063, actor_role="warden",
        reports=("registration_trends",)),
    "TC-BR-064": _case_064,
    "TC-BR-065": _case_065,
    "TC-BR-066": _case_066,
    "TC-BR-067": _case_067,
    "TC-BR-068": _case_068,
    "TC-BR-071": partial(_case_071_072_073, role="student"),
    "TC-BR-072": partial(_case_071_072_073, role="caretaker"),
    "TC-BR-073": partial(_case_071_072_073, role="warden"),
    "TC-BR-075": partial(_case_075_076, role="caretaker"),
    "TC-BR-076": partial(_case_075_076, role="non_caretaker"),
    "TC-BR-077": _case_077,
    "TC-BR-080": partial(_case_080_081, answer="Yes"),
    "TC-BR-081": partial(_case_080_081, answer="No"),
    "TC-BR-082": _case_082,
    "TC-BR-083": partial(_case_083_084, own=True),
    "TC-BR-084": partial(_case_083_084, own=False),
}


@pytest.mark.parametrize(
    "test_case",
    [pytest.param(case, id=case["id"]) for case in CASES],
)
def test_frozen_br_case(test_case, stub_iam, user_ref):
    case_id = test_case["id"]
    if case_id in BLOCKED:
        pytest.skip(BLOCKED[case_id])
    assert case_id in HANDLERS, f"No handler for frozen BR case {case_id}"
    HANDLERS[case_id](BRFixture(stub_iam, user_ref))
