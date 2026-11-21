from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from django.utils import timezone
from freezegun import freeze_time
from rest_framework.test import APIClient

from conftest import make_session
from fusion_auth.principal import Principal
from modules.directory.models import UserRef
from modules.mms.models import (
    Announcement,
    BillingInput,
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

DESIGN = Path(__file__).resolve().parents[3] / "a8_design" / "UC_DESIGN.json"
_DESIGN = json.loads(DESIGN.read_text())["design"]
_TEST_CASES = _DESIGN["test_cases"]

PERMISSION = {
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

BLOCKED = {
    test_case["id"]: test_case["unresolved_reason"]
    for test_case in _TEST_CASES
    if test_case["status"] == "blocked"
}


class UCHarness:
    def __init__(self, stub_iam, user_ref):
        self.stub_iam = stub_iam
        self.user_ref = user_ref
        self.directory_users = {}

    def client(self, user_id, role="student", *, permissions=None, modules=True):
        kind = "student" if role == "student" else "staff"
        self.stub_iam(
            make_session(
                user_id=user_id,
                kind=kind,
                roles=(role,),
                active_role=role,
                modules=("mess_management",) if modules else (),
                permissions=PERMISSION[role] if permissions is None else permissions,
            ),
            users=self.directory_users,
        )
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token uc-test")
        return client

    def identity(self, user_id, kind="student"):
        row, _ = UserRef.objects.get_or_create(
            user_id=user_id,
            defaults={
                "username": f"uc-{user_id}",
                "display_name": f"UC user {user_id}",
                "kind": kind,
            },
        )
        return row

    def employee(self, user_id):
        row = self.identity(user_id, kind="faculty")
        self.directory_users[user_id] = self.user_ref(
            row.user_id, name=row.display_name, kind="faculty")
        return row

    def active_role(self, user_id, role):
        now = timezone.now()
        return RoleAssignment.objects.create(
            role=role,
            user_id=user_id,
            starts_at=now - timedelta(days=1),
            ends_at=now + timedelta(days=90),
            is_current=True,
            assigned_by_user_id=9000,
        )

    def actor(self, user_id=3001):
        return Principal.from_session(
            make_session(
                user_id=user_id,
                kind="staff",
                roles=("caretaker",),
                active_role="caretaker",
                modules=("mess_management",),
                permissions=PERMISSION["caretaker"],
            )
        )

    def enrollment(self, user_id, *, registered_at=None, deregistered_at=None):
        return Enrollment.objects.create(
            user_id=user_id,
            registered_at=registered_at or timezone.now() - timedelta(days=30),
            deregistered_at=deregistered_at,
        )

    def window(self, cycle="UC-Cycle"):
        now = timezone.now()
        return RegistrationWindow.objects.create(
            cycle=cycle,
            opens_at=now - timedelta(days=1),
            closes_at=now + timedelta(days=1),
            opened_by_user_id=3001,
        )


def _entries(item="Meal"):
    return [
        {"day": day, "meal": meal, "item": item}
        for day in range(7)
        for meal in ("breakfast", "lunch", "dinner")
    ]


def _create_menu(item="Meal"):
    today = timezone.localdate()
    week_start = today + timedelta(days=7 - today.weekday())
    week = MenuWeek.objects.create(
        week_start=week_start, updated_by_user_id=3001)
    MenuEntry.objects.bulk_create(
        MenuEntry(week=week, day=entry["day"], meal=entry["meal"], item=item)
        for entry in _entries()
    )
    return week


def _create_survey(*, deadline=None):
    today = timezone.localdate()
    return VacationSurvey.objects.create(
        title="UC vacation survey",
        vacation_starts_on=today + timedelta(days=20),
        vacation_ends_on=today + timedelta(days=30),
        deadline=deadline or timezone.now() + timedelta(days=5),
        created_by_user_id=3001,
    )


def _create_bill(user_id, *, year=2026, month=9, total="1200.00", status="published"):
    return MonthlyBill.objects.create(
        user_id=user_id,
        year=year,
        month=month,
        daily_rate=Decimal("100.00"),
        served_days=12,
        total=Decimal(total),
        status=status,
        finalized_by_user_id=3001 if status != "generated" else None,
    )


def _submit_rebate(client, *, reason="medical", explanation="", start=None, end=None):
    start = start or (timezone.localdate() + timedelta(days=2)).isoformat()
    end = end or (timezone.localdate() + timedelta(days=4)).isoformat()
    return client.post(
        "/api/v1/mms/rebates",
        {"reason": reason, "explanation": explanation,
         "starts_on": start, "ends_on": end},
        format="json",
    )


def _submit_food(client, *, requested_for=None, reason="illness"):
    requested_date = requested_for or (
        timezone.localdate() + timedelta(days=2)).isoformat()
    return client.post(
        "/api/v1/mms/special-food",
        {
            "reason": reason,
            "details": "UC test request",
            "requested_for": requested_date,
        },
        format="json",
    )


def _decide_request(client, request, approve):
    return client.post(
        f"/api/v1/mms/requests/{request.pk}/decision",
        {"approve": approve},
        format="json",
    )


def _decide_special(client, request, approve, **payload):
    return client.post(
        f"/api/v1/mms/special-food/{request.pk}/decision",
        {"approve": approve, **payload},
        format="json",
    )


def _post_window(client, *, cycle="UC-Cycle", opens_at=None, closes_at=None):
    now = timezone.now()
    return client.post(
        "/api/v1/mms/registration-windows",
        {
            "cycle": cycle,
            "opens_at": opens_at or (now - timedelta(days=1)).isoformat(),
            "closes_at": closes_at or (now + timedelta(days=1)).isoformat(),
        },
        format="json",
    )


def _report(client, report):
    return client.get(f"/api/v1/mms/reports?type={report}")


def _case_001(h):
    h.employee(4101)
    h.employee(4102)
    h.active_role(4102, "warden")
    ends_at = timezone.now() + timedelta(days=30)
    response = h.client(9000, "admin").post(
        "/api/v1/mms/roles",
        {"role": "caretaker", "user_id": 4101,
         "ends_at": ends_at.isoformat()},
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["user_id"] == 4101
    assert RoleAssignment.objects.filter(role="caretaker", is_current=True).count() == 1
    assert RoleAssignment.objects.filter(role="warden", is_current=True).count() == 1
    assignment = RoleAssignment.objects.get(role="caretaker", is_current=True)
    assert assignment.starts_at <= timezone.now() < assignment.ends_at
    assert assignment.ends_at == ends_at


def _case_002(h):
    h.employee(4102)
    previous = h.active_role(4101, "caretaker")
    window = h.window()
    request = StudentRequest.objects.create(user_id=5101, kind="registration", window=window)
    RequestHistory.objects.create(request=request, status="pending", actor_user_id=5101)
    response = h.client(9000, "admin").post(
        "/api/v1/mms/roles",
        {"role": "caretaker", "user_id": 4102,
         "ends_at": (timezone.now() + timedelta(days=30)).isoformat()},
        format="json",
    )
    assert response.status_code == 201
    previous.refresh_from_db()
    assert previous.is_current is False
    assert h.client(4102, "caretaker").get("/api/v1/mms/overview").status_code == 200
    decision = _decide_request(h.client(4102, "caretaker"), request, True)
    assert decision.status_code == 200
    assert decision.json()["decided_by_user_id"] == 4102


def _case_003(h):
    h.employee(4101)
    h.employee(4102)
    incumbent = h.active_role(4101, "caretaker")
    response = h.client(9000, "admin").post(
        "/api/v1/mms/roles",
        {"role": "caretaker", "user_id": 4102,
         "ends_at": (timezone.now() + timedelta(days=30)).isoformat()},
        format="json",
    )
    assert response.status_code == 409
    incumbent.refresh_from_db()
    assert incumbent.is_current


def _case_004(h):
    response = h.client(9000, "admin").post(
        "/api/v1/mms/roles",
        {"role": "caretaker", "user_id": 4999,
         "ends_at": (timezone.now() + timedelta(days=30)).isoformat()},
        format="json",
    )
    assert response.status_code == 409
    assert not RoleAssignment.objects.exists()


def _case_005(h):
    h.employee(4101)
    h.active_role(4101, "caretaker")
    response = h.client(4101, "caretaker").post(
        "/api/v1/mms/roles",
        {"role": "warden", "user_id": 4101,
         "ends_at": (timezone.now() + timedelta(days=30)).isoformat()},
        format="json",
    )
    assert response.status_code == 403
    assert RoleAssignment.objects.filter(role="warden").count() == 0


def _case_006(h):
    h.active_role(3001, "caretaker")
    response = _post_window(h.client(3001, "caretaker"))
    assert response.status_code == 201
    assert RegistrationWindow.objects.filter(cycle="UC-Cycle").exists()
    window = RegistrationWindow.objects.get(cycle="UC-Cycle")
    assert window.opens_at < timezone.now() < window.closes_at


def _case_007(h):
    h.active_role(3001, "caretaker")
    response = h.client(3001, "caretaker").post(
        "/api/v1/mms/registration-windows",
        {"cycle": "", "opens_at": "", "closes_at": ""},
        format="json",
    )
    assert response.status_code >= 400
    assert not RegistrationWindow.objects.exists()


def _case_008(h):
    response = _post_window(h.client(1001, "student"))
    assert response.status_code == 403
    assert not RegistrationWindow.objects.exists()


def _case_009(h):
    window = h.window()
    response = h.client(1001).post(
        "/api/v1/mms/requests", {"kind": "registration", "window_id": window.pk},
        format="json",
    )
    assert response.status_code == 201
    assert response.json()["status"] == "pending"
    event = NotificationOutbox.objects.get(
        topic="request.submitted", recipient_user_id=1001)
    assert event.dedupe_key and event.subject and event.body


def _case_010(h):
    response = h.client(1001).post(
        "/api/v1/mms/requests", {"kind": "registration", "window_id": 999999},
        format="json",
    )
    assert response.status_code == 409
    assert not StudentRequest.objects.exists()


def _case_012(h):
    window = h.window()
    response = h.client(4101, "caretaker").post(
        "/api/v1/mms/requests",
        {"kind": "registration", "window_id": window.pk},
        format="json",
    )
    assert response.status_code == 403
    assert not StudentRequest.objects.exists()


def _case_013(h):
    h.active_role(3001, "caretaker")
    request = StudentRequest.objects.create(
        user_id=1001, kind="registration", window=h.window())
    response = _decide_request(h.client(3001, "caretaker"), request, True)
    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert NotificationOutbox.objects.filter(
        topic="request.decided", recipient_user_id=1001).exists()


def _case_014(h):
    h.active_role(3001, "caretaker")
    request = StudentRequest.objects.create(
        user_id=1001, kind="registration", window=h.window())
    response = _decide_request(h.client(3001, "caretaker"), request, False)
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert NotificationOutbox.objects.filter(
        topic="request.decided", recipient_user_id=1001).exists()


def _case_015(h):
    h.active_role(3001, "caretaker")
    request = StudentRequest.objects.create(
        user_id=1001, kind="registration", window=h.window(), status="approved")
    response = _decide_request(h.client(3001, "caretaker"), request, True)
    assert response.status_code == 409
    request.refresh_from_db()
    assert request.status == "approved"


def _case_016(h):
    request = StudentRequest.objects.create(
        user_id=1001, kind="registration", window=h.window())
    response = _decide_request(h.client(3002, "warden"), request, True)
    assert response.status_code == 403
    request.refresh_from_db()
    assert request.status == "pending"


def _case_017(h):
    h.enrollment(1001)
    response = h.client(1001).post(
        "/api/v1/mms/requests", {"kind": "deregistration"}, format="json")
    assert response.status_code == 201
    assert response.json()["status"] == "pending"
    assert NotificationOutbox.objects.filter(
        topic="request.submitted", recipient_user_id=1001).exists()


def _case_018(h):
    response = h.client(1001).post(
        "/api/v1/mms/requests", {"kind": "deregistration"}, format="json")
    assert response.status_code == 409
    assert not StudentRequest.objects.exists()


def _case_019(h):
    h.enrollment(1001)
    response = h.client(3001, "caretaker").post(
        "/api/v1/mms/requests", {"kind": "deregistration"}, format="json")
    assert response.status_code == 403
    assert not StudentRequest.objects.exists()


def _case_020(h):
    h.active_role(3001, "caretaker")
    h.enrollment(1001)
    request = StudentRequest.objects.create(user_id=1001, kind="deregistration")
    response = _decide_request(h.client(3001, "caretaker"), request, True)
    assert response.status_code == 200
    assert response.json()["status"] == "approved_awaiting_effect"
    assert response.json()["effective_at"]
    assert NotificationOutbox.objects.filter(
        topic="request.decided", recipient_user_id=1001).exists()


def _case_021(h):
    h.active_role(3001, "caretaker")
    enrollment = h.enrollment(1001)
    request = StudentRequest.objects.create(user_id=1001, kind="deregistration")
    response = _decide_request(h.client(3001, "caretaker"), request, False)
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    enrollment.refresh_from_db()
    assert enrollment.deregistered_at is None


def _case_022(h):
    h.active_role(3001, "caretaker")
    request = StudentRequest.objects.create(
        user_id=1001, kind="deregistration", status="rejected")
    response = _decide_request(h.client(3001, "caretaker"), request, False)
    assert response.status_code == 409
    request.refresh_from_db()
    assert request.status == "rejected"


def _case_023(h):
    h.active_role(3002, "warden")
    request = StudentRequest.objects.create(
        user_id=1001, kind="deregistration")
    response = _decide_request(h.client(3002, "warden"), request, True)
    assert response.status_code == 403
    request.refresh_from_db()
    assert request.status == "pending"


def _case_024(h):
    h.active_role(3002, "warden")
    registration = StudentRequest.objects.create(
        user_id=1001, kind="registration", window=h.window())
    response = h.client(3002, "warden").get("/api/v1/mms/requests")
    assert response.status_code == 200
    ids = {row["id"] for row in response.json()["results"]}
    assert registration.pk in ids


def _case_025(h):
    h.active_role(3002, "warden")
    request = StudentRequest.objects.create(
        user_id=1001, kind="registration", window=h.window())
    RequestHistory.objects.create(request=request, status="pending", actor_user_id=1001)
    response = _decide_request(h.client(3002, "warden"), request, True)
    assert response.status_code == 403
    request.refresh_from_db()
    assert request.status == "pending"
    assert list(request.history.values_list("status", flat=True)) == ["pending"]


def _case_026(h):
    h.active_role(3001, "caretaker")
    h.identity(1001, "student")
    entries = _entries("Added")
    week_start = timezone.localdate() + timedelta(
        days=7 - timezone.localdate().weekday())
    first = h.client(3001, "caretaker").post(
        "/api/v1/mms/menu",
        {"week_start": week_start.isoformat(), "entries": entries},
        format="json",
    )
    assert first.status_code == 201
    modified = [dict(entry, item="Modified") for entry in entries]
    second = h.client(3001, "caretaker").post(
        "/api/v1/mms/menu",
        {"week_start": week_start.isoformat(), "entries": modified},
        format="json",
    )
    assert second.status_code == 201
    reduced = modified[:-1]
    third = h.client(3001, "caretaker").post(
        "/api/v1/mms/menu",
        {"week_start": week_start.isoformat(), "entries": reduced},
        format="json",
    )
    assert third.status_code == 409
    updated = h.client(3001, "caretaker").post(
        "/api/v1/mms/menu",
        {"week_start": week_start.isoformat(), "entries": modified},
        format="json",
    )
    assert updated.status_code == 201
    week = MenuWeek.objects.get(week_start=week_start)
    assert week.published_at is not None
    assert week.entries.count() == 21
    assert week.entries.filter(item="Modified").count() == 21
    assert NotificationOutbox.objects.filter(
        topic="menu.updated", recipient_user_id=1001).exists()


def _case_027(h):
    h.active_role(3001, "caretaker")
    week = _create_menu("Original")
    entries = _entries("Invalid")
    entries.pop()
    response = h.client(3001, "caretaker").post(
        "/api/v1/mms/menu",
        {"week_start": week.week_start.isoformat(), "entries": entries},
        format="json",
    )
    assert response.status_code == 409
    week.refresh_from_db()
    assert week.entries.count() == 21
    assert not week.entries.filter(item="Invalid").exists()


def _case_028(h):
    h.identity(1001, "student")
    week = _create_menu("Original")
    response = h.client(1001).post(
        "/api/v1/mms/menu",
        {"week_start": week.week_start.isoformat(), "entries": _entries("Changed")},
        format="json",
    )
    assert response.status_code == 403
    assert week.entries.filter(item="Original").count() == 21
    assert not week.entries.filter(item="Changed").exists()


def _case_029(h):
    _create_menu("Published menu")
    response = h.client(1001).get("/api/v1/mms/menu")
    assert response.status_code == 200
    rows = response.json()["results"]
    assert len(rows) == 1
    entries = rows[0]["entries"]
    assert len(entries) == 21
    assert {(item["day"], item["meal"]) for item in entries} == {
        (day, meal) for day in range(7)
        for meal in ("breakfast", "lunch", "dinner")
    }


def _case_030(h):
    h.active_role(3001, "caretaker")
    _create_menu("Published menu")
    response = h.client(3001, "caretaker").get("/api/v1/mms/menu")
    assert response.status_code == 200
    assert len(response.json()["results"]) == 1


def _case_031(h):
    h.active_role(3002, "warden")
    _create_menu("Published menu")
    response = h.client(3002, "warden").get("/api/v1/mms/menu")
    assert response.status_code == 200
    assert len(response.json()["results"]) == 1


def _case_034(h):
    h.active_role(3001, "caretaker")
    bill = _create_bill(1001, status="generated")
    client = h.client(3001, "caretaker")
    finalized = client.post(
        f"/api/v1/mms/bills/{bill.pk}/finalize", {}, format="json")
    assert finalized.status_code == 200
    published = client.post(
        f"/api/v1/mms/bills/{bill.pk}/publish", {}, format="json")
    assert published.status_code == 200
    assert published.json()["status"] == "published"
    assert h.client(1001).get("/api/v1/mms/bills").json()["results"]
    assert NotificationOutbox.objects.filter(
        topic="bill.published", recipient_user_id=1001).exists()


def _case_035(h):
    h.active_role(3001, "caretaker")
    bill = _create_bill(1001, status="generated")
    response = h.client(3001, "caretaker").post(
        f"/api/v1/mms/bills/{bill.pk}/publish", {}, format="json")
    assert response.status_code == 409
    bill.refresh_from_db()
    assert bill.status == "generated"
    assert not NotificationOutbox.objects.exists()


def _case_036(h):
    bill = _create_bill(1001, status="generated")
    response = h.client(1001).post(
        f"/api/v1/mms/bills/{bill.pk}/finalize", {}, format="json")
    assert response.status_code == 403
    bill.refresh_from_db()
    assert bill.status == "generated"


def _case_037(h):
    _create_bill(1001)
    _create_bill(2002, total="500.00")
    response = h.client(1001).get("/api/v1/mms/bills")
    assert response.status_code == 200
    assert [row["user_id"] for row in response.json()["results"]] == [1001]
    assert Decimal(str(response.json()["balance"])) == Decimal("1200.00")


def _case_038(h):
    response = h.client(1001).get("/api/v1/mms/bills")
    assert response.status_code == 200
    assert response.json()["results"] == []


def _case_039(h):
    _create_bill(2002)
    response = h.client(1001).get("/api/v1/mms/bills")
    assert response.status_code == 200
    assert all(row["user_id"] != 2002 for row in response.json()["results"])


def _case_040(h):
    response = h.client(1001).post(
        "/api/v1/mms/feedback", {"message": "Mess service feedback"}, format="json")
    assert response.status_code == 201
    assert response.json()["message"] == "Mess service feedback"
    assert Feedback.objects.filter(user_id=1001).exists()


def _case_041(h):
    response = h.client(1001).post(
        "/api/v1/mms/feedback", {"message": ""}, format="json")
    assert response.status_code >= 400
    assert not Feedback.objects.exists()


def _case_042(h):
    response = h.client(3001, "caretaker").post(
        "/api/v1/mms/feedback", {"message": "Not a Student submission"}, format="json")
    assert response.status_code == 403
    assert not Feedback.objects.exists()


def _case_043(h):
    h.active_role(3001, "caretaker")
    Feedback.objects.create(user_id=1001, message="Stored feedback")
    response = h.client(3001, "caretaker").get("/api/v1/mms/feedback")
    assert response.status_code == 200
    assert response.json()["results"][0]["message"] == "Stored feedback"


def _case_044(h):
    h.active_role(3002, "warden")
    Feedback.objects.create(user_id=1001, message="Stored feedback")
    response = h.client(3002, "warden").get("/api/v1/mms/feedback")
    assert response.status_code == 200
    assert response.json()["results"][0]["message"] == "Stored feedback"


def _case_045(h):
    h.active_role(3001, "caretaker")
    response = h.client(3001, "caretaker").get("/api/v1/mms/feedback")
    assert response.status_code == 200
    assert response.json()["results"] == []


def _case_046(h):
    Feedback.objects.create(user_id=1001, message="Private feedback")
    response = h.client(2002).get("/api/v1/mms/feedback")
    assert response.status_code == 403
    assert Feedback.objects.filter(user_id=1001).exists()


def _case_047_050(h, case_id):
    h.enrollment(1001)
    if case_id == "TC-UC-047":
        args = {}
    elif case_id == "TC-UC-048":
        args = {"reason": "institute_leave"}
    elif case_id == "TC-UC-049":
        args = {"reason": "family_function"}
    else:
        args = {"reason": "other", "explanation": "Conference attendance"}
    response = _submit_rebate(h.client(1001), **args)
    assert response.status_code == 201
    assert response.json()["status"] == "pending"
    if case_id == "TC-UC-050":
        assert response.json()["explanation"] == "Conference attendance"
    assert NotificationOutbox.objects.filter(
        topic="rebate.submitted", recipient_user_id=1001).exists()


def _case_051(h):
    h.enrollment(1001)
    start = timezone.localdate() + timedelta(days=2)
    response = _submit_rebate(
        h.client(1001), start=start.isoformat(),
        end=(start + timedelta(days=1)).isoformat())
    assert response.status_code == 409
    assert not RebateRequest.objects.exists()


def _case_052(h):
    h.enrollment(1001)
    today = timezone.localdate()
    response = _submit_rebate(
        h.client(1001), start=today.isoformat(),
        end=(today + timedelta(days=2)).isoformat())
    assert response.status_code == 409
    assert not RebateRequest.objects.exists()


def _case_053(h):
    h.enrollment(1001)
    start = timezone.localdate() + timedelta(days=2)
    RebateRequest.objects.create(
        user_id=1001, reason="medical",
        starts_on=start, ends_on=start + timedelta(days=5),
        status="approved")
    response = _submit_rebate(
        h.client(1001), reason="institute_leave",
        start=(start + timedelta(days=3)).isoformat(),
        end=(start + timedelta(days=7)).isoformat())
    assert response.status_code == 409
    assert RebateRequest.objects.filter(user_id=1001).count() == 1


def _case_054(h):
    h.enrollment(1001)
    response = _submit_rebate(h.client(1001), reason="other")
    assert response.status_code == 409
    assert not RebateRequest.objects.exists()


def _case_055(h):
    h.active_role(3001, "caretaker")
    response = _submit_rebate(h.client(3001, "caretaker"))
    assert response.status_code == 403
    assert not RebateRequest.objects.exists()


def _case_056_057(h, approve):
    h.active_role(3001, "caretaker")
    starts_on = timezone.localdate() + timedelta(days=2)
    rebate = RebateRequest.objects.create(
        user_id=1001, reason="medical",
        starts_on=starts_on, ends_on=starts_on + timedelta(days=2))
    response = h.client(3001, "caretaker").post(
        f"/api/v1/mms/rebates/{rebate.pk}/decision",
        {"approve": approve}, format="json")
    assert response.status_code == 200
    assert response.json()["status"] == ("approved" if approve else "rejected")
    assert NotificationOutbox.objects.filter(
        topic="rebate.decided", recipient_user_id=1001).exists()


def _case_059(h):
    h.active_role(3001, "caretaker")
    starts_on = timezone.localdate() + timedelta(days=2)
    rebate = RebateRequest.objects.create(
        user_id=1001, reason="medical",
        starts_on=starts_on, ends_on=starts_on + timedelta(days=2),
        status="approved")
    response = h.client(3001, "caretaker").post(
        f"/api/v1/mms/rebates/{rebate.pk}/decision",
        {"approve": False}, format="json")
    assert response.status_code == 409
    rebate.refresh_from_db()
    assert rebate.status == "approved"


def _case_060(h):
    starts_on = timezone.localdate() + timedelta(days=2)
    rebate = RebateRequest.objects.create(
        user_id=1001, reason="medical",
        starts_on=starts_on, ends_on=starts_on + timedelta(days=2))
    response = h.client(3002, "warden").post(
        f"/api/v1/mms/rebates/{rebate.pk}/decision",
        {"approve": True}, format="json")
    assert response.status_code == 403
    rebate.refresh_from_db()
    assert rebate.status == "pending"


def _case_061_062_064(h, case_id):
    if case_id == "TC-UC-064":
        response = h.client(1001).post(
            "/api/v1/mms/vacation-surveys",
            {
                "title": "UC survey", "vacation_starts_on": "2026-12-10",
                "vacation_ends_on": "2026-12-20",
                "deadline": (timezone.now() + timedelta(days=3)).isoformat(),
            },
            format="json",
        )
        assert response.status_code == 403
        assert not VacationSurvey.objects.exists()
        return
    h.active_role(3001, "caretaker")
    h.enrollment(1001)
    h.identity(1001, "student")
    payload = {
        "title": "UC survey",
        "vacation_starts_on": (timezone.localdate() + timedelta(days=20)).isoformat(),
        "vacation_ends_on": (timezone.localdate() + timedelta(days=30)).isoformat(),
        "deadline": (timezone.now() + timedelta(days=3)).isoformat(),
    }
    if case_id == "TC-UC-062":
        payload.pop("deadline")
    response = h.client(3001, "caretaker").post(
        "/api/v1/mms/vacation-surveys", payload, format="json")
    if case_id == "TC-UC-062":
        assert response.status_code >= 400
        assert not VacationSurvey.objects.exists()
    else:
        assert response.status_code == 201
        survey = VacationSurvey.objects.get()
        assert survey.deadline
        assert NotificationOutbox.objects.filter(
            topic="vacation.created", recipient_user_id=1001).exists()


def _case_065_068_069_070(h, case_id):
    survey = _create_survey()
    if case_id in {"TC-UC-065", "TC-UC-066"}:
        h.enrollment(1001)
        response = h.client(1001).post(
            f"/api/v1/mms/vacation-surveys/{survey.pk}/responses",
            {"response": "Yes" if case_id == "TC-UC-065" else "No"},
            format="json",
        )
        assert response.status_code == 200
        assert VacationResponse.objects.get(survey=survey, user_id=1001).response == (
            "yes" if case_id == "TC-UC-065" else "no")
    elif case_id == "TC-UC-067":
        response = h.client(1001).post(
            f"/api/v1/mms/vacation-surveys/{survey.pk}/responses",
            {"response": "yes"}, format="json")
        assert response.status_code >= 400
        assert not VacationResponse.objects.exists()
    elif case_id == "TC-UC-068":
        h.enrollment(1001)
        survey.deadline = timezone.now() - timedelta(seconds=1)
        survey.save(update_fields=["deadline"])
        response = h.client(1001).post(
            f"/api/v1/mms/vacation-surveys/{survey.pk}/responses",
            {"response": "yes"}, format="json")
        assert response.status_code == 409
        assert not VacationResponse.objects.exists()
    elif case_id == "TC-UC-069":
        h.enrollment(1001)
        response = h.client(1001).post(
            f"/api/v1/mms/vacation-surveys/{survey.pk}/responses",
            {"response": "maybe"}, format="json")
        assert response.status_code == 409
        assert not VacationResponse.objects.exists()
    else:
        h.enrollment(1001)
        response = h.client(3001, "caretaker").post(
            f"/api/v1/mms/vacation-surveys/{survey.pk}/responses",
            {"response": "yes"}, format="json")
        assert response.status_code == 403
        assert not VacationResponse.objects.exists()


def _case_071(h):
    h.active_role(3001, "caretaker")
    survey = _create_survey()
    VacationResponse.objects.create(survey=survey, user_id=1001, response="yes")
    VacationResponse.objects.create(
        survey=survey, user_id=1002, response="no", is_default=True)
    response = h.client(3001, "caretaker").get(
        f"/api/v1/mms/vacation-surveys/{survey.pk}/responses")
    assert response.status_code == 200
    assert {row["response"] for row in response.json()["results"]} == {"yes", "no"}


def _case_072(h):
    h.active_role(3001, "caretaker")
    survey = _create_survey()
    response = h.client(3001, "caretaker").get(
        f"/api/v1/mms/vacation-surveys/{survey.pk}/responses")
    assert response.status_code == 200
    assert response.json()["results"] == []


def _case_074_077(h, case_id):
    if case_id == "TC-UC-077":
        response = _submit_food(h.client(3001, "caretaker"))
        assert response.status_code == 403
        assert not SpecialFoodRequest.objects.exists()
        return
    reason = "illness" if case_id == "TC-UC-074" else "personal_event"
    response = _submit_food(h.client(1001), reason=reason)
    assert response.status_code == 201
    assert response.json()["status"] == "requested"
    assert SpecialFoodHistory.objects.filter(
        request_id=response.json()["id"], status="requested").exists()
    assert NotificationOutbox.objects.filter(
        topic="special_food.submitted", recipient_user_id=1001).exists()


def _case_076(h):
    with freeze_time("2026-10-10T12:00:00Z"):
        response = _submit_food(h.client(1001), requested_for="2026-10-10")
    assert response.status_code == 409
    assert not SpecialFoodRequest.objects.exists()


def _case_078(h):
    h.active_role(3001, "caretaker")
    request = SpecialFoodRequest.objects.create(
        user_id=1001, reason="illness", requested_for=date(2026, 12, 1))
    response = _decide_special(h.client(3001, "caretaker"), request, True)
    assert response.status_code == 200
    assert response.json()["status"] == "approved"
    assert NotificationOutbox.objects.filter(
        topic="special_food.decided", recipient_user_id=1001).exists()


def _case_079(h):
    h.active_role(3001, "caretaker")
    request = SpecialFoodRequest.objects.create(
        user_id=1001, reason="illness", requested_for=date(2026, 12, 1))
    response = _decide_special(h.client(3001, "caretaker"), request, False)
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert NotificationOutbox.objects.filter(
        topic="special_food.decided", recipient_user_id=1001).exists()


def _case_080(h):
    h.active_role(3001, "caretaker")
    request = SpecialFoodRequest.objects.create(
        user_id=1001, reason="illness", requested_for=date(2026, 12, 1),
        status="approved", charge_amount=Decimal("10.00"))
    response = _decide_special(h.client(3001, "caretaker"), request, False)
    assert response.status_code == 409
    request.refresh_from_db()
    assert request.status == "approved"


def _case_082(h):
    request = SpecialFoodRequest.objects.create(
        user_id=1001, reason="illness", requested_for=date(2026, 12, 1))
    response = _decide_special(h.client(3002, "warden"), request, False)
    assert response.status_code == 403
    request.refresh_from_db()
    assert request.status == "requested"


def _case_083_084(h, case_id):
    h.active_role(3001, "caretaker")
    request = SpecialFoodRequest.objects.create(
        user_id=1001, reason="illness", requested_for=date(2026, 12, 1),
        status="approved", charge_amount=Decimal("10.00"))
    status_value = "served" if case_id == "TC-UC-083" else "cancelled"
    response = h.client(3001, "caretaker").post(
        f"/api/v1/mms/special-food/{request.pk}/fulfillment",
        {"status": status_value}, format="json")
    assert response.status_code == 200
    assert response.json()["status"] == status_value
    assert NotificationOutbox.objects.filter(
        topic="special_food.fulfillment", recipient_user_id=1001).exists()


def _case_085(h):
    h.active_role(3001, "caretaker")
    request = SpecialFoodRequest.objects.create(
        user_id=1001, reason="illness", requested_for=date(2026, 12, 1),
        status="requested")
    response = h.client(3001, "caretaker").post(
        f"/api/v1/mms/special-food/{request.pk}/fulfillment",
        {"status": "served"}, format="json")
    assert response.status_code == 409
    request.refresh_from_db()
    assert request.status == "requested"


def _case_088_089_090(h, case_id):
    if case_id == "TC-UC-090":
        response = h.client(1001).post(
            "/api/v1/mms/announcements",
            {"title": "Notice", "body": "Mess notice"}, format="json")
        assert response.status_code == 403
        assert not Announcement.objects.exists()
        return
    role = "caretaker" if case_id == "TC-UC-088" else "warden"
    h.active_role(3001, role)
    h.identity(1001, "student")
    response = h.client(3001, role).post(
        "/api/v1/mms/announcements",
        {"title": "Mess notice", "body": "Service update"}, format="json")
    assert response.status_code == 201
    assert response.json()["published_by_role"] == role
    assert response.json()["published_at"]
    assert NotificationOutbox.objects.filter(
        topic="announcement.published", recipient_user_id=1001).exists()


def _case_091_093(h):
    announcement = Announcement.objects.create(
        title="History", body="Notice", published_by_user_id=3001,
        published_by_role="caretaker", published_at=timezone.now())
    response = h.client(1001).get("/api/v1/mms/announcements")
    assert response.status_code == 200
    rows = response.json()["results"]
    assert len(rows) == 1 and rows[0]["id"] == announcement.pk


def _case_092(h):
    for role, user_id in (("caretaker", 3001), ("warden", 3002)):
        h.active_role(user_id, role)
        response = h.client(user_id, role).get("/api/v1/mms/announcements")
        assert response.status_code == 200
        assert response.json()["results"] == []


def _case_096(h):
    h.active_role(3002, "warden")
    h.enrollment(1001)
    response = _report(h.client(3002, "warden"), "registered")
    assert response.status_code == 200
    assert [row["user_id"] for row in response.json()["results"]] == [1001]


def _case_097(h):
    h.active_role(3002, "warden")
    RebateRequest.objects.create(
        user_id=1001, reason="medical",
        starts_on=date(2026, 10, 10), ends_on=date(2026, 10, 12))
    response = _report(h.client(3002, "warden"), "rebates")
    assert response.status_code == 200
    assert response.json()["results"][0]["user_id"] == 1001


def _case_098(h):
    h.active_role(3002, "warden")
    survey = _create_survey()
    VacationResponse.objects.create(survey=survey, user_id=1001, response="yes")
    response = _report(h.client(3002, "warden"), "vacation")
    assert response.status_code == 200
    row = next(item for item in response.json()["results"] if item["id"] == survey.pk)
    assert row["yes"] == 1 and row["no"] == 0


def _case_099(h):
    h.active_role(3002, "warden")
    response = _report(h.client(3002, "warden"), "registered")
    assert response.status_code == 200
    assert response.json()["results"] == []


def _case_100(h):
    h.active_role(3001, "caretaker")
    response = _report(h.client(3001, "caretaker"), "registered")
    assert response.status_code == 403


def _case_101_103(h, report):
    h.active_role(3001, "caretaker")
    if report == "registration_trends":
        StudentRequest.objects.create(
            user_id=1001, kind="registration", window=h.window())
    else:
        _create_bill(1001)
    response = _report(h.client(3001, "caretaker"), report)
    assert response.status_code == 200
    assert response.json()["results"]


def _case_102(h):
    h.active_role(3001, "caretaker")
    SpecialFoodRequest.objects.create(
        user_id=1001, reason="illness", requested_for=date(2026, 12, 1))
    response = _report(h.client(3001, "caretaker"), "special_meals")
    assert response.status_code == 200
    assert response.json()["results"][0]["user_id"] == 1001


def _case_104(h):
    h.active_role(3001, "caretaker")
    response = _report(h.client(3001, "caretaker"), "registration_trends")
    assert response.status_code == 200
    assert response.json()["results"] == []


def _case_105(h):
    h.active_role(3002, "warden")
    response = _report(h.client(3002, "warden"), "registration_trends")
    assert response.status_code == 403


def _case_106(h):
    request = StudentRequest.objects.create(
        user_id=1001, kind="registration", window=h.window())
    RequestHistory.objects.create(request=request, status="pending", actor_user_id=1001)
    response = h.client(1001).get("/api/v1/mms/requests")
    assert response.status_code == 200
    rows = response.json()["results"]
    assert len(rows) == 1 and rows[0]["id"] == request.pk
    assert rows[0]["status"] == "pending" and rows[0]["history"]


def _case_107(h):
    response = h.client(1001).get("/api/v1/mms/requests")
    assert response.status_code == 200
    assert response.json()["results"] == []


def _case_108(h):
    StudentRequest.objects.create(
        user_id=2002, kind="deregistration")
    response = h.client(1001).get("/api/v1/mms/requests?user_id=2002")
    assert response.status_code == 200
    assert all(row["user_id"] == 1001 for row in response.json()["results"])


def _case_109(h):
    from modules.mms.services.operations import activate_deregistrations

    enrollment = h.enrollment(1001)
    request = StudentRequest.objects.create(
        user_id=1001, kind="deregistration",
        status="approved_awaiting_effect",
        effective_at=timezone.now() - timedelta(seconds=1))
    assert activate_deregistrations() == 1
    request.refresh_from_db()
    enrollment.refresh_from_db()
    assert request.status == "effective"
    assert enrollment.deregistered_at == request.effective_at
    assert request.history.filter(status="effective").exists()


def _case_110(h):
    from modules.mms.services.operations import activate_deregistrations

    enrollment = h.enrollment(1001)
    request = StudentRequest.objects.create(
        user_id=1001, kind="deregistration",
        status="rejected", effective_at=timezone.now() - timedelta(days=1))
    assert activate_deregistrations() == 0
    request.refresh_from_db()
    enrollment.refresh_from_db()
    assert request.status == "rejected"
    assert enrollment.deregistered_at is None


def _case_111(h, monkeypatch):
    from modules.mms.services import operations

    enrollment = h.enrollment(1001)
    request = StudentRequest.objects.create(
        user_id=1001, kind="deregistration",
        status="approved_awaiting_effect",
        effective_at=timezone.now() - timedelta(seconds=1))

    def fail_history(*args, **kwargs):
        raise RuntimeError("injected UC event failure")

    monkeypatch.setattr(operations, "_record_request", fail_history)
    with pytest.raises(RuntimeError, match="injected UC event failure"):
        operations.activate_deregistrations()
    enrollment.refresh_from_db()
    request.refresh_from_db()
    assert enrollment.deregistered_at is None
    assert request.status == "approved_awaiting_effect"


def _case_112(h):
    from modules.mms.services.operations import default_vacation_responses

    h.active_role(3001, "caretaker")
    h.enrollment(1001)
    survey = _create_survey(deadline=timezone.now() - timedelta(seconds=1))
    assert default_vacation_responses() == 1
    response = VacationResponse.objects.get(survey=survey, user_id=1001)
    assert response.response == "no" and response.is_default
    listed = h.client(3001, "caretaker").get(
        f"/api/v1/mms/vacation-surveys/{survey.pk}/responses")
    assert listed.status_code == 200


def _case_113(h):
    from modules.mms.services.operations import default_vacation_responses

    h.enrollment(1001)
    survey = _create_survey(deadline=timezone.now() - timedelta(seconds=1))
    explicit = VacationResponse.objects.create(
        survey=survey, user_id=1001, response="yes", is_default=False)
    assert default_vacation_responses() == 0
    explicit.refresh_from_db()
    assert explicit.response == "yes" and not explicit.is_default


def _case_114(h):
    from modules.mms.services.operations import default_vacation_responses

    h.enrollment(1001)
    survey = _create_survey(deadline=timezone.now() - timedelta(seconds=1))
    VacationResponse.objects.create(survey=survey, user_id=1001, response="no")
    assert default_vacation_responses() == 0
    assert VacationResponse.objects.filter(survey=survey).count() == 1


def _case_115(h, monkeypatch):
    from modules.mms.services import operations

    h.enrollment(1001)
    survey = _create_survey(deadline=timezone.now() - timedelta(seconds=1))
    explicit = VacationResponse.objects.create(
        survey=survey, user_id=1002, response="yes", is_default=False)

    def fail_bulk_create(*args, **kwargs):
        raise RuntimeError("injected UC deadline failure")

    monkeypatch.setattr(VacationResponse.objects, "bulk_create", fail_bulk_create)
    with pytest.raises(RuntimeError, match="injected UC deadline failure"):
        operations.default_vacation_responses()
    explicit.refresh_from_db()
    assert explicit.response == "yes" and not explicit.is_default
    assert VacationResponse.objects.filter(survey=survey).count() == 1


def _case_116(h):
    from modules.mms.services.operations import reject_expired_special_food

    request = SpecialFoodRequest.objects.create(
        user_id=1001, reason="illness", requested_for=date(2026, 12, 1))
    SpecialFoodHistory.objects.create(request=request, status="requested", actor_user_id=1001)
    now = request.created_at + timedelta(hours=2)
    assert reject_expired_special_food(now=now, decision_hours=1) == 1
    request.refresh_from_db()
    assert request.status == "rejected"
    assert request.history.filter(status="rejected").exists()
    assert NotificationOutbox.objects.filter(
        topic="special_food.decided", recipient_user_id=1001).exists()


def _case_117(h):
    from modules.mms.services.operations import reject_expired_special_food

    request = SpecialFoodRequest.objects.create(
        user_id=1001, reason="illness", requested_for=date(2026, 12, 1),
        status="approved")
    assert reject_expired_special_food(
        now=timezone.now() + timedelta(days=1), decision_hours=1) == 0
    request.refresh_from_db()
    assert request.status == "approved"


def _case_118(h, monkeypatch):
    from modules.mms.services import notifications, operations

    request = SpecialFoodRequest.objects.create(
        user_id=1001, reason="illness", requested_for=date(2026, 12, 1))
    SpecialFoodHistory.objects.create(request=request, status="requested", actor_user_id=1001)

    def fail_notify(**kwargs):
        raise RuntimeError("injected UC timeout failure")

    monkeypatch.setattr(notifications, "notify_user", fail_notify)
    with pytest.raises(RuntimeError, match="injected UC timeout failure"):
        operations.reject_expired_special_food(
            now=request.created_at + timedelta(hours=2), decision_hours=1)
    request.refresh_from_db()
    assert request.status == "requested"
    assert request.history.count() == 1


def _case_120(h):
    from modules.mms.services.operations import generate_bills

    h.enrollment(
        1001,
        registered_at=timezone.make_aware(datetime(2026, 9, 1, 0, 0)))
    bills = generate_bills(
        system_event=True, year=2026, month=9,
        inputs=[{"user_id": 1001, "daily_rate": "100", "served_days": 25}],
    )
    assert len(bills) == 1
    bill = bills[0]
    assert bill.status == "generated"
    assert bill.total == Decimal("2500.00")
    assert bill.published_at is None


def _case_121(h):
    from modules.mms.services.operations import generate_ready_bills

    h.enrollment(
        1001,
        registered_at=timezone.make_aware(datetime(2026, 9, 1, 0, 0)))
    BillingInput.objects.create(
        user_id=1001, year=2026, month=9,
        daily_rate=Decimal("100"), served_days=25, recorded_by_user_id=3001)
    h.enrollment(1002, registered_at=timezone.make_aware(datetime(2026, 9, 1, 0, 0)))
    assert generate_ready_bills(today=date(2026, 10, 1)) == 0
    assert not MonthlyBill.objects.exists()


def _case_122(h, monkeypatch):
    from modules.mms.domain import rules
    from modules.mms.services import operations

    h.enrollment(
        1001,
        registered_at=timezone.make_aware(datetime(2026, 9, 1, 0, 0)))
    h.enrollment(
        1002,
        registered_at=timezone.make_aware(datetime(2026, 9, 1, 0, 0)))
    original = rules.calculate_bill
    calls = 0

    def fail_second(**kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("injected UC billing failure")
        return original(**kwargs)

    monkeypatch.setattr(operations, "calculate_bill", fail_second)
    with pytest.raises(RuntimeError, match="injected UC billing failure"):
        operations.generate_bills(
            system_event=True, year=2026, month=9,
            inputs=[
                {"user_id": 1001, "daily_rate": "100", "served_days": 25},
                {"user_id": 1002, "daily_rate": "100", "served_days": 25},
            ],
        )
    assert not MonthlyBill.objects.exists()
    assert Enrollment.objects.count() == 2


def _case_123(h):
    from modules.mms.services.operations import send_vacation_reminder

    h.active_role(3001, "caretaker")
    h.enrollment(1001)
    h.enrollment(1002)
    survey = _create_survey()
    VacationResponse.objects.create(survey=survey, user_id=1001, response="yes")
    count = send_vacation_reminder(actor=h.actor(), survey_id=survey.pk)
    assert count == 1
    assert NotificationOutbox.objects.filter(
        topic="vacation.reminder", recipient_user_id=1002).exists()
    assert not NotificationOutbox.objects.filter(
        topic="vacation.reminder", recipient_user_id=1001).exists()
    assert VacationResponse.objects.count() == 1


def _case_124(h):
    from core.api.exceptions import NotFoundError
    from modules.mms.services.operations import send_vacation_reminder

    h.active_role(3001, "caretaker")
    survey = _create_survey(deadline=timezone.now() - timedelta(seconds=1))
    with pytest.raises(NotFoundError):
        send_vacation_reminder(actor=h.actor(), survey_id=survey.pk)
    assert not NotificationOutbox.objects.exists()


def _case_127(h):
    response = h.client(9000, "admin").get("/api/v1/mms/requests")
    assert response.status_code == 403


def _case_128(h):
    h.active_role(3002, "warden")
    week = _create_menu()
    response = h.client(3002, "warden").post(
        "/api/v1/mms/menu",
        {"week_start": week.week_start.isoformat(), "entries": _entries("Changed")},
        format="json",
    )
    assert response.status_code == 403
    assert not MenuEntry.objects.filter(week=week, item="Changed").exists()


def _dispatch(case_id, h, monkeypatch):
    if case_id in {"TC-UC-047", "TC-UC-048", "TC-UC-049", "TC-UC-050"}:
        return _case_047_050(h, case_id)
    if case_id in {"TC-UC-056", "TC-UC-057"}:
        return _case_056_057(h, case_id == "TC-UC-056")
    if case_id in {"TC-UC-061", "TC-UC-062", "TC-UC-064"}:
        return _case_061_062_064(h, case_id)
    if case_id in {"TC-UC-065", "TC-UC-066", "TC-UC-067", "TC-UC-068",
                   "TC-UC-069", "TC-UC-070"}:
        return _case_065_068_069_070(h, case_id)
    if case_id in {"TC-UC-074", "TC-UC-075", "TC-UC-077"}:
        return _case_074_077(h, case_id)
    if case_id in {"TC-UC-083", "TC-UC-084"}:
        return _case_083_084(h, case_id)
    if case_id in {"TC-UC-088", "TC-UC-089", "TC-UC-090"}:
        return _case_088_089_090(h, case_id)
    if case_id in {"TC-UC-091", "TC-UC-093"}:
        return _case_091_093(h)
    if case_id in {"TC-UC-101", "TC-UC-103"}:
        return _case_101_103(h, "registration_trends" if case_id == "TC-UC-101"
                             else "billing_summary")
    if case_id == "TC-UC-111":
        return _case_111(h, monkeypatch)
    if case_id == "TC-UC-115":
        return _case_115(h, monkeypatch)
    if case_id == "TC-UC-122":
        return _case_122(h, monkeypatch)
    if case_id == "TC-UC-118":
        return _case_118(h, monkeypatch)

    runner = globals().get(f"_case_{int(case_id[-3:]):03}")
    if runner is not None:
        return runner(h)
    if case_id == "TC-UC-025":
        return _case_025(h)
    if case_id == "TC-UC-028":
        return _case_028(h)
    if case_id == "TC-UC-029":
        return _case_029(h)
    if case_id == "TC-UC-030":
        return _case_030(h)
    if case_id == "TC-UC-031":
        return _case_031(h)
    if case_id == "TC-UC-101":
        return _case_101_103(h, "registration_trends")
    if case_id == "TC-UC-103":
        return _case_101_103(h, "billing_summary")
    if case_id == "TC-UC-109":
        return _case_109(h)
    if case_id == "TC-UC-110":
        return _case_110(h)
    if case_id == "TC-UC-112":
        return _case_112(h)
    if case_id == "TC-UC-113":
        return _case_113(h)
    if case_id == "TC-UC-114":
        return _case_114(h)
    if case_id == "TC-UC-116":
        return _case_116(h)
    if case_id == "TC-UC-117":
        return _case_117(h)
    if case_id == "TC-UC-120":
        return _case_120(h)
    if case_id == "TC-UC-121":
        return _case_121(h)
    if case_id == "TC-UC-123":
        return _case_123(h)
    if case_id == "TC-UC-124":
        return _case_124(h)
    if case_id == "TC-UC-127":
        return _case_127(h)
    if case_id == "TC-UC-128":
        return _case_128(h)
    raise AssertionError(f"No UC test handler for frozen case {case_id}")


@pytest.mark.parametrize(
    "test_case",
    [pytest.param(case, id=case["id"]) for case in _TEST_CASES],
)
def test_frozen_uc_case(test_case, stub_iam, user_ref, monkeypatch):
    case_id = test_case["id"]
    if case_id in BLOCKED:
        pytest.skip(BLOCKED[case_id])
    _dispatch(case_id, UCHarness(stub_iam, user_ref), monkeypatch)
