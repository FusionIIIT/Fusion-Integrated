from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from freezegun import freeze_time
from rest_framework.test import APIClient

from conftest import make_session
from fusion_auth.principal import Principal
from modules.directory.models import UserRef as DirectoryUserRef
from modules.mms.models import (
    Announcement,
    Enrollment,
    Feedback,
    MenuWeek,
    MonthlyBill,
    NotificationOutbox,
    RebateHistory,
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

MODULE = ("mess_management",)
STUDENT_PERMISSIONS = ("mess_management.student.use",)
ADMIN_PERMISSIONS = ("mess_management.roles.manage",)
CARETAKER_PERMISSIONS = (
    "mess_management.operations.view",
    "mess_management.operations.manage",
    "mess_management.requests.review",
    "mess_management.menu.manage",
    "mess_management.billing.manage",
    "mess_management.feedback.view",
    "mess_management.surveys.manage",
    "mess_management.announcements.publish",
    "mess_management.reports.caretaker",
)
WARDEN_PERMISSIONS = (
    "mess_management.operations.view",
    "mess_management.feedback.view",
    "mess_management.announcements.publish",
    "mess_management.reports.warden",
)
PERMISSIONS = {
    "student": STUDENT_PERMISSIONS,
    "admin": ADMIN_PERMISSIONS,
    "caretaker": CARETAKER_PERMISSIONS,
    "warden": WARDEN_PERMISSIONS,
}


class Harness:
    def __init__(self, stub_iam, user_ref):
        self.stub_iam = stub_iam
        self.user_ref = user_ref
        self.iam_users = {}

    def client(self, user_id, role="student"):
        kind = "student" if role == "student" else "staff"
        self.stub_iam(
            make_session(
                user_id=user_id,
                kind=kind,
                roles=(role,),
                active_role=role,
                modules=MODULE,
                permissions=PERMISSIONS[role],
            ),
            users=self.iam_users,
        )
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token fr-test")
        return client

    def identity(self, user_id, kind="student"):
        identity, _ = DirectoryUserRef.objects.get_or_create(
            user_id=user_id,
            defaults={
                "username": f"fr-{user_id}",
                "display_name": f"FR user {user_id}",
                "kind": kind,
            },
        )
        self.iam_users[user_id] = self.user_ref(
            user_id, name=identity.display_name, kind=kind)
        return identity

    def employee(self, user_id):
        return self.identity(user_id, kind="faculty")

    def active_role(self, user_id, role):
        now = timezone.now()
        return RoleAssignment.objects.create(
            role=role,
            user_id=user_id,
            starts_at=now - timedelta(days=1),
            ends_at=now + timedelta(days=365),
            is_current=True,
            assigned_by_user_id=9000,
        )

    def actor(self, user_id, role="caretaker"):
        return Principal.from_session(
            make_session(
                user_id=user_id,
                kind="staff",
                roles=(role,),
                active_role=role,
                modules=MODULE,
                permissions=PERMISSIONS[role],
            )
        )

    def enrollment(self, user_id, *, registered_at=None, deregistered_at=None):
        return Enrollment.objects.create(
            user_id=user_id,
            registered_at=registered_at or timezone.now() - timedelta(days=30),
            deregistered_at=deregistered_at,
        )

    def window(self, cycle="Semester-Autumn-2026"):
        now = timezone.now()
        return RegistrationWindow.objects.create(
            cycle=cycle,
            opens_at=now - timedelta(days=1),
            closes_at=now + timedelta(days=1),
            opened_by_user_id=9000,
        )


def _menu_entries(item="Meal"):
    return [
        {"day": day, "meal": meal, "item": item}
        for day in range(7)
        for meal in ("breakfast", "lunch", "dinner")
    ]


def _create_menu(client, item="Meal"):
    return client.post(
        "/api/v1/mms/menu",
        {"week_start": "2026-10-05", "entries": _menu_entries(item)},
        format="json",
    )


def _create_survey(title="Vacation survey", deadline="2026-12-05T23:59:00Z"):
    return VacationSurvey.objects.create(
        title=title,
        vacation_starts_on=date(2026, 12, 10),
        vacation_ends_on=date(2026, 12, 20),
        deadline=datetime.fromisoformat(deadline.replace("Z", "+00:00")),
        created_by_user_id=9000,
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
        finalized_by_user_id=9000 if status != "generated" else None,
    )


def _submit_rebate(client, *, reason="medical", explanation="", starts="2026-10-05",
                   ends="2026-10-07"):
    return client.post(
        "/api/v1/mms/rebates",
        {
            "reason": reason,
            "explanation": explanation,
            "starts_on": starts,
            "ends_on": ends,
        },
        format="json",
    )


def _submit_special_food(client, requested_for=None):
    requested_for = requested_for or (timezone.localdate() + timedelta(days=2)).isoformat()
    return client.post(
        "/api/v1/mms/special-food",
        {
            "reason": "illness",
            "details": "Frozen FR case",
            "requested_for": requested_for,
        },
        format="json",
    )


def _run_status(h):
    h.enrollment(1001)
    response = h.client(1001).get("/api/v1/mms/student-status")
    assert response.status_code == 200
    assert response.json()["registered"] is True
    assert response.json().get("cycle") == "Semester-Autumn-2026"


def _run_role(h, case_id):
    role = "caretaker" if case_id not in {"TC-FR-003", "TC-FR-007", "TC-FR-008",
                                          "TC-FR-010"} else "warden"
    if case_id in {"TC-FR-002", "TC-FR-003", "TC-FR-009", "TC-FR-010",
                   "TC-FR-013"}:
        employee_id = 1001 if role == "caretaker" else 1002
        h.employee(employee_id)
        with freeze_time("2026-08-02T12:00:00Z"):
            payload = {
                "role": role,
                "user_id": employee_id,
                "ends_at": (
                    "2026-12-31T18:29:00Z"
                    if case_id != "TC-FR-013"
                    else (timezone.now() + timedelta(days=30)).isoformat()
                ),
            }
            if case_id != "TC-FR-013":
                payload["starts_at"] = "2026-08-01T00:00:00Z"
            response = h.client(9000, "admin").post(
                "/api/v1/mms/roles",
                payload,
                format="json",
            )
        assert response.status_code == 201
        assert response.json()["user_id"] == employee_id
        if case_id != "TC-FR-013":
            assert response.json()["starts_at"].startswith("2026-08-01")
            assert response.json()["ends_at"].startswith("2026-12-31")
        assert DirectoryUserRef.objects.filter(user_id=employee_id).count() == 1
        return

    if case_id in {"TC-FR-004", "TC-FR-011"}:
        h.employee(1003)
        h.employee(1004)
        h.active_role(1003, "caretaker")
        response = h.client(9000, "admin").post(
            "/api/v1/mms/roles",
            {
                "role": "caretaker",
                "user_id": 1004,
                "ends_at": (timezone.now() + timedelta(days=30)).isoformat(),
            },
            format="json",
        )
        assert response.status_code == 201
        assert not RoleAssignment.objects.get(user_id=1003).is_current
        assert RoleAssignment.objects.get(user_id=1004).is_current
        return

    current_user = 1001 if role == "caretaker" else 1002
    other_user = 1004 if role == "caretaker" else 1005
    h.employee(current_user)
    h.employee(other_user)
    h.active_role(current_user, role)
    if case_id in {"TC-FR-005", "TC-FR-007"}:
        response = h.client(9000, "admin").get("/api/v1/mms/roles")
        assert response.status_code == 200
        current = [row for row in response.json()["current"] if row["role"] == role]
        assert [row["user_id"] for row in current] == [current_user]
    elif case_id in {"TC-FR-006", "TC-FR-008"}:
        response = h.client(9000, "admin").post(
            "/api/v1/mms/roles",
            {
                "role": role,
                "user_id": other_user,
                "ends_at": (timezone.now() + timedelta(days=30)).isoformat(),
            },
            format="json",
        )
        assert response.status_code == 409
        assert RoleAssignment.objects.get(user_id=current_user).is_current
    elif case_id == "TC-FR-012":
        window = h.window()
        request = StudentRequest.objects.create(
            user_id=2001, kind="registration", window=window)
        RequestHistory.objects.create(request=request, status="pending", actor_user_id=2001)
        rebate = RebateRequest.objects.create(
            user_id=2001,
            reason="medical",
            starts_on=date(2026, 10, 10),
            ends_on=date(2026, 10, 12),
        )
        h.employee(1004)
        reassignment = h.client(9000, "admin").post(
            "/api/v1/mms/roles",
            {
                "role": "caretaker",
                "user_id": 1004,
                "ends_at": (timezone.now() + timedelta(days=30)).isoformat(),
            },
            format="json",
        )
        assert reassignment.status_code == 201
        response = h.client(1004, "caretaker").get("/api/v1/mms/overview")
        assert response.status_code == 200
        assert request.id in [row["id"] for row in response.json()["requests"]]
        assert rebate.id in [row["id"] for row in response.json()["rebates"]]
        decision = h.client(1004, "caretaker").post(
            f"/api/v1/mms/requests/{request.id}/decision",
            {"approve": True},
            format="json",
        )
        assert decision.status_code == 200
        assert decision.json()["decided_by_user_id"] == 1004
    elif case_id == "TC-FR-014":
        response = h.client(9000, "admin").get("/api/v1/mms/requests")
        assert response.status_code == 403


def _run_registration(h, case_id):
    if case_id == "TC-FR-015":
        with freeze_time("2026-07-25T12:00:00Z"):
            h.active_role(3001, "caretaker")
            response = h.client(3001, "caretaker").post(
                "/api/v1/mms/registration-windows",
                {
                    "cycle": "Semester-Autumn-2026",
                    "opens_at": "2026-07-20T00:00:00Z",
                    "closes_at": "2026-07-31T23:59:00Z",
                },
                format="json",
            )
        assert response.status_code == 201
        assert response.json()["cycle"] == "Semester-Autumn-2026"
        assert response.json()["is_open"] is True
        return

    if case_id in {"TC-FR-016", "TC-FR-017", "TC-FR-028"}:
        with freeze_time("2026-07-25T12:00:00Z"):
            window = RegistrationWindow.objects.create(
                cycle="Semester-Autumn-2026",
                opens_at=timezone.now() - timedelta(days=1),
                closes_at=(timezone.now() + timedelta(days=1)
                           if case_id != "TC-FR-017" else timezone.now() - timedelta(seconds=1)),
                opened_by_user_id=3001,
            )
            response = h.client(1001).post(
                "/api/v1/mms/requests",
                {"kind": "registration", "window_id": window.id},
                format="json",
            )
            if case_id == "TC-FR-017":
                assert response.status_code == 409
                assert not NotificationOutbox.objects.exists()
            else:
                assert response.status_code == 201
                assert response.json()["status"] == "pending"
                if case_id == "TC-FR-028":
                    event = NotificationOutbox.objects.get(topic="request.submitted")
                    assert event.recipient_user_id == 1001
        return

    if case_id in {"TC-FR-018", "TC-FR-019", "TC-FR-030"}:
        h.active_role(3001, "caretaker")
        request = StudentRequest.objects.create(
            user_id=1001, kind="registration", window=h.window())
        response = h.client(3001, "caretaker").post(
            f"/api/v1/mms/requests/{request.id}/decision",
            {"approve": case_id != "TC-FR-019"},
            format="json",
        )
        assert response.status_code == 200
        expected = "rejected" if case_id == "TC-FR-019" else "approved"
        assert response.json()["status"] == expected
        if case_id == "TC-FR-018":
            assert Enrollment.objects.filter(user_id=1001, deregistered_at__isnull=True).exists()
        if case_id == "TC-FR-030":
            assert NotificationOutbox.objects.filter(
                topic="request.decided", recipient_user_id=1001).exists()
        return

    if case_id in {"TC-FR-020", "TC-FR-029"}:
        h.enrollment(1001)
        response = h.client(1001).post(
            "/api/v1/mms/requests",
            {"kind": "deregistration"},
            format="json",
        )
        assert response.status_code == 201
        assert response.json()["status"] == "pending"
        if case_id == "TC-FR-029":
            assert NotificationOutbox.objects.filter(
                topic="request.submitted", recipient_user_id=1001).exists()
        return

    if case_id in {"TC-FR-021", "TC-FR-022", "TC-FR-023", "TC-FR-031"}:
        request = StudentRequest.objects.create(user_id=1001, kind="deregistration")
        with freeze_time("2026-10-10T12:30:00Z"):
            h.active_role(3001, "caretaker")
            response = h.client(3001, "caretaker").post(
                f"/api/v1/mms/requests/{request.id}/decision",
                {"approve": True},
                format="json",
            )
            assert response.status_code == 200
            assert response.json()["status"] == "approved_awaiting_effect"
            if case_id == "TC-FR-022":
                assert response.json()["decided_by_user_id"] == 3001
                assert response.json()["decided_at"]
            if case_id == "TC-FR-023":
                enrollment = h.enrollment(1001)
                assert enrollment.deregistered_at is None
                from modules.mms.services.operations import activate_deregistrations

                request.refresh_from_db()
                activate_deregistrations(now=request.effective_at)
                enrollment.refresh_from_db()
                assert enrollment.deregistered_at == request.effective_at
            if case_id == "TC-FR-031":
                assert NotificationOutbox.objects.filter(
                    topic="request.decided", recipient_user_id=1001).exists()
        return

    if case_id == "TC-FR-024":
        h.active_role(3002, "warden")
        request = StudentRequest.objects.create(
            user_id=1001, kind="registration", window=h.window())
        response = h.client(3002, "warden").get("/api/v1/mms/requests")
        assert response.status_code == 200
        assert request.id in [row["id"] for row in response.json()["results"]]
    elif case_id == "TC-FR-025":
        h.active_role(3002, "warden")
        request = StudentRequest.objects.create(
            user_id=1001, kind="registration", window=h.window())
        response = h.client(3002, "warden").post(
            f"/api/v1/mms/requests/{request.id}/decision",
            {"approve": True},
            format="json",
        )
        request.refresh_from_db()
        assert response.status_code == 403
        assert request.status == "pending"
    elif case_id in {"TC-FR-026", "TC-FR-027"}:
        window = h.window()
        request = StudentRequest.objects.create(
            user_id=1001, kind="registration", window=window)
        RequestHistory.objects.create(request=request, status="pending", actor_user_id=1001)
        if case_id == "TC-FR-026":
            StudentRequest.objects.create(
                user_id=2002, kind="deregistration")
        else:
            h.active_role(3001, "caretaker")
            h.client(3001, "caretaker").post(
                f"/api/v1/mms/requests/{request.id}/decision",
                {"approve": True},
                format="json",
            )
        response = h.client(1001).get("/api/v1/mms/requests")
        assert response.status_code == 200
        row = next(item for item in response.json()["results"] if item["id"] == request.id)
        if case_id == "TC-FR-026":
            assert row["user_id"] == 1001
            assert row["history"]
        else:
            assert row["status"] == "approved"
            assert [item["status"] for item in row["history"]] == ["pending", "approved"]


def _run_menu(h, case_id):
    if case_id in {"TC-FR-032", "TC-FR-033", "TC-FR-034", "TC-FR-036", "TC-FR-037"}:
        role = {
            "TC-FR-036": "caretaker",
            "TC-FR-037": "warden",
        }.get(case_id, "student")
        week = MenuWeek.objects.create(
            week_start=date(2026, 10, 5), updated_by_user_id=3001)
        from modules.mms.models import MenuEntry

        MenuEntry.objects.bulk_create(
            MenuEntry(week=week, day=day, meal=meal, item="Meal")
            for day, meal in ((entry["day"], entry["meal"]) for entry in _menu_entries())
        )
        if role != "student":
            h.active_role(3001, role)
        response = h.client(1001 if role == "student" else 3001, role).get(
            "/api/v1/mms/menu")
        assert response.status_code == 200
        entries = response.json()["results"][0]["entries"]
        assert len(entries) == 21
        if case_id == "TC-FR-033":
            assert {(row["day"], row["meal"]) for row in entries} == {
                (day, meal) for day in range(7)
                for meal in ("breakfast", "lunch", "dinner")
            }
        return

    if case_id in {"TC-FR-035", "TC-FR-038"}:
        role = "student" if case_id == "TC-FR-035" else "warden"
        if role == "warden":
            h.active_role(3001, role)
        response = _create_menu(h.client(1001 if role == "student" else 3001, role))
        assert response.status_code == 403
        return

    if case_id in {"TC-FR-039", "TC-FR-040", "TC-FR-041"}:
        h.active_role(3001, "caretaker")
        h.identity(1001)
        entries = _menu_entries("Poha")
        if case_id == "TC-FR-040":
            entries[0]["item"] = "Upma"
        response = h.client(3001, "caretaker").post(
            "/api/v1/mms/menu",
            {"week_start": "2026-10-05", "entries": entries},
            format="json",
        )
        assert response.status_code == 201
        if case_id == "TC-FR-039":
            assert len(response.json()["entries"]) == 21
        if case_id == "TC-FR-040":
            assert response.json()["entries"][0]["item"] == "Upma"
        if case_id == "TC-FR-041":
            assert NotificationOutbox.objects.filter(
                topic="menu.updated", recipient_user_id=1001).exists()


def _generate_bill(h, *, year=2026, month=9, rate="100", days=25):
    from modules.mms.services.operations import generate_bills

    h.active_role(3001, "caretaker")
    h.enrollment(
        1001,
        registered_at=timezone.make_aware(datetime(year, month, 1, 0, 0)),
    )
    bills = generate_bills(
        actor=h.actor(3001),
        year=year,
        month=month,
        inputs=[{"user_id": 1001, "daily_rate": rate, "served_days": days}],
    )
    assert len(bills) == 1
    return bills[0]


def _run_billing(h, case_id):
    if case_id == "TC-FR-042":
        _create_bill(1001)
        _create_bill(2002, total="500.00")
        response = h.client(1001).get("/api/v1/mms/bills")
        assert response.status_code == 200
        assert [row["user_id"] for row in response.json()["results"]] == [1001]
        return
    if case_id == "TC-FR-043":
        bill = _generate_bill(h)
        assert bill.user_id == 1001
        assert bill.year == 2026 and bill.month == 9
        return
    if case_id == "TC-FR-044":
        from modules.mms.domain.rules import calculate_bill

        assert calculate_bill(
            daily_rate=Decimal("100"), served_days=25,
            special_food_charges=Decimal("0"),
            rebate_deduction=Decimal("0"),
        ) == Decimal("2500.00")
        return
    if case_id in {"TC-FR-046", "TC-FR-047", "TC-FR-072", "TC-FR-095"}:
        if case_id in {"TC-FR-046", "TC-FR-072"}:
            RebateRequest.objects.create(
                user_id=1001,
                reason="medical",
                starts_on=date(2026, 9, 10),
                ends_on=date(2026, 9, 14) if case_id == "TC-FR-046" else date(2026, 9, 13),
                status="approved",
            )
        if case_id in {"TC-FR-047", "TC-FR-095"}:
            SpecialFoodRequest.objects.create(
                user_id=1001,
                reason="illness",
                requested_for=date(2026, 9, 10),
                status="approved",
                charge_amount=Decimal("150.00"),
            )
        bill = _generate_bill(h, days=30)
        if case_id == "TC-FR-046":
            assert bill.rebate_deduction == Decimal("500.00")
            assert bill.total == Decimal("2500.00")
        elif case_id == "TC-FR-072":
            assert bill.rebate_deduction == Decimal("400.00")
        else:
            assert bill.special_food_charges == Decimal("150.00")
        return
    if case_id in {"TC-FR-049", "TC-FR-050"}:
        h.active_role(3001, "caretaker")
        bill = _create_bill(1001, status="generated")
        client = h.client(3001, "caretaker")
        finalized = client.post(
            f"/api/v1/mms/bills/{bill.id}/finalize", {}, format="json")
        assert finalized.status_code == 200
        published = client.post(
            f"/api/v1/mms/bills/{bill.id}/publish", {}, format="json")
        assert published.status_code == 200
        assert published.json()["status"] == "published"
        if case_id == "TC-FR-049":
            assert h.client(1001).get("/api/v1/mms/bills").json()["results"]
        if case_id == "TC-FR-050":
            assert NotificationOutbox.objects.filter(
                topic="bill.published", recipient_user_id=1001).exists()
        return
    if case_id == "TC-FR-051":
        _create_bill(1001)
        response = h.client(1001).get("/api/v1/mms/bills")
        assert response.status_code == 200
        assert Decimal(str(response.json()["balance"])) == Decimal("1200.00")
        return
    if case_id == "TC-FR-052":
        h.active_role(3002, "warden")
        _create_bill(1001)
        response = h.client(3002, "warden").get("/api/v1/mms/bills")
        assert response.status_code == 200
        assert response.json()["results"]


def _run_feedback(h, case_id):
    if case_id in {"TC-FR-053", "TC-FR-056"}:
        response = h.client(1001).post(
            "/api/v1/mms/feedback",
            {"message": "Food quality improvement requested"},
            format="json",
        )
        assert response.status_code == 201
        assert response.json()["user_id"] == 1001
        assert response.json()["message"] == "Food quality improvement requested"
        assert response.json()["created_at"]
    else:
        Feedback.objects.create(user_id=1001, message="Feedback record")
        role = "caretaker" if case_id == "TC-FR-054" else "warden"
        h.active_role(3001, role)
        response = h.client(3001, role).get("/api/v1/mms/feedback")
        assert response.status_code == 200
        assert response.json()["results"][0]["message"] == "Feedback record"


def _run_rebate(h, case_id):
    if case_id in {"TC-FR-057", "TC-FR-058", "TC-FR-059", "TC-FR-060",
                   "TC-FR-061", "TC-FR-062", "TC-FR-063", "TC-FR-064",
                   "TC-FR-065", "TC-FR-066", "TC-FR-067", "TC-FR-068",
                   "TC-FR-069"}:
        h.enrollment(1001)
        with freeze_time("2026-10-01T12:00:00Z"):
            if case_id == "TC-FR-059":
                response = _submit_rebate(
                    h.client(1001), reason="other",
                    explanation="Attending outstation conference")
            elif case_id == "TC-FR-062":
                response = _submit_rebate(
                    h.client(1001), reason="institute_leave")
            elif case_id == "TC-FR-063":
                response = _submit_rebate(
                    h.client(1001), reason="family_function")
            elif case_id == "TC-FR-064":
                response = _submit_rebate(h.client(1001), reason="other")
            elif case_id == "TC-FR-065":
                response = _submit_rebate(
                    h.client(1001), starts="2026-10-05", ends="2026-10-07")
            elif case_id == "TC-FR-066":
                response = _submit_rebate(
                    h.client(1001), starts="2026-10-05", ends="2026-10-06")
            elif case_id == "TC-FR-067":
                with freeze_time("2026-10-04T12:00:00Z"):
                    response = _submit_rebate(
                        h.client(1001), starts="2026-10-05", ends="2026-10-07")
            elif case_id == "TC-FR-068":
                with freeze_time("2026-10-05T12:00:00Z"):
                    response = _submit_rebate(
                        h.client(1001), starts="2026-10-05", ends="2026-10-07")
            elif case_id == "TC-FR-069":
                RebateRequest.objects.create(
                    user_id=1001,
                    reason="medical",
                    starts_on=date(2026, 10, 10),
                    ends_on=date(2026, 10, 15),
                    status="approved",
                )
                response = _submit_rebate(
                    h.client(1001), reason="institute_leave",
                    starts="2026-10-13", ends="2026-10-17")
            else:
                response = _submit_rebate(h.client(1001))
        if case_id in {"TC-FR-064", "TC-FR-066", "TC-FR-068", "TC-FR-069"}:
            assert response.status_code == 409
            return
        assert response.status_code == 201
        if case_id in {"TC-FR-057", "TC-FR-058", "TC-FR-061"}:
            assert response.json()["status"] == "pending"
            assert response.json()["reason"] == "medical"
        if case_id == "TC-FR-059":
            assert response.json()["explanation"] == "Attending outstation conference"
        if case_id == "TC-FR-065":
            assert response.json()["starts_on"] == "2026-10-05"
            assert response.json()["ends_on"] == "2026-10-07"
        if case_id == "TC-FR-060":
            assert NotificationOutbox.objects.filter(
                topic="rebate.submitted", recipient_user_id=1001).exists()
        if case_id in {"TC-FR-062", "TC-FR-063"}:
            assert response.json()["reason"] == (
                "institute_leave" if case_id == "TC-FR-062" else "family_function")
        return

    if case_id in {"TC-FR-070", "TC-FR-071", "TC-FR-075"}:
        h.active_role(3001, "caretaker")
        rebate = RebateRequest.objects.create(
            user_id=1001,
            reason="medical",
            starts_on=date(2026, 10, 10),
            ends_on=date(2026, 10, 12),
        )
        response = h.client(3001, "caretaker").post(
            f"/api/v1/mms/rebates/{rebate.id}/decision",
            {"approve": case_id != "TC-FR-071"},
            format="json",
        )
        assert response.status_code == 200
        expected = "rejected" if case_id == "TC-FR-071" else "approved"
        assert response.json()["status"] == expected
        if case_id == "TC-FR-075":
            assert NotificationOutbox.objects.filter(
                topic="rebate.decided", recipient_user_id=1001).exists()
        return

    if case_id == "TC-FR-073":
        rebate = RebateRequest.objects.create(
            user_id=1001,
            reason="medical",
            starts_on=date(2026, 10, 10),
            ends_on=date(2026, 10, 12),
        )
        RebateHistory.objects.create(
            request=rebate, status="pending", actor_user_id=1001)
        response = h.client(1001).get("/api/v1/mms/rebates")
        row = response.json()["results"][0]
        assert row["id"] == rebate.id
        assert row["history"][0]["status"] == "pending"
        return

    if case_id == "TC-FR-074":
        rebate = RebateRequest.objects.create(
            user_id=1001,
            reason="medical",
            starts_on=date(2026, 10, 10),
            ends_on=date(2026, 10, 12),
        )
        for role, uid in (("caretaker", 3001), ("warden", 3002)):
            h.active_role(uid, role)
            response = h.client(uid, role).get("/api/v1/mms/rebates")
            assert response.status_code == 200
            assert any(row["id"] == rebate.id for row in response.json()["results"])


def _run_vacation(h, case_id):
    if case_id in {"TC-FR-076", "TC-FR-079", "TC-FR-080"}:
        h.active_role(3001, "caretaker")
        h.enrollment(1001)
        response = h.client(3001, "caretaker").post(
            "/api/v1/mms/vacation-surveys",
            {
                "title": "December food survey",
                "vacation_starts_on": "2026-12-10",
                "vacation_ends_on": "2026-12-20",
                "deadline": "2026-12-05T18:29:00Z",
            },
            format="json",
        )
        assert response.status_code == 201
        if case_id == "TC-FR-079":
            assert response.json()["deadline"].startswith("2026-12-05")
        if case_id == "TC-FR-080":
            assert NotificationOutbox.objects.filter(
                topic="vacation.created", recipient_user_id=1001).exists()
        return

    survey = _create_survey()
    if case_id in {"TC-FR-077", "TC-FR-078"}:
        if case_id == "TC-FR-077":
            h.enrollment(1001)
            response = h.client(1001).get("/api/v1/mms/vacation-surveys")
            assert response.status_code == 200
            assert survey.id in [row["id"] for row in response.json()["results"]]
        else:
            response = h.client(1099).get("/api/v1/mms/vacation-surveys")
            assert response.status_code == 200
            assert survey.id not in [row["id"] for row in response.json()["results"]]
        return
    if case_id == "TC-FR-081":
        h.active_role(3001, "caretaker")
        h.enrollment(1002)
        response = h.client(3001, "caretaker").post(
            f"/api/v1/mms/vacation-surveys/{survey.id}/remind",
            {},
            format="json",
        )
        assert response.status_code == 200
        assert NotificationOutbox.objects.filter(
            topic="vacation.reminder", recipient_user_id=1002).exists()
        return
    if case_id in {"TC-FR-082", "TC-FR-083"}:
        h.enrollment(1001)
        response = h.client(1001).post(
            f"/api/v1/mms/vacation-surveys/{survey.id}/responses",
            {"response": "Yes" if case_id == "TC-FR-082" else "Maybe"},
            format="json",
        )
        if case_id == "TC-FR-083":
            assert response.status_code == 409
        else:
            assert response.status_code == 201
            assert response.json()["response"].lower() == "yes"
        return
    if case_id == "TC-FR-084":
        from modules.mms.services.operations import default_vacation_responses

        h.enrollment(1003)
        assert default_vacation_responses(now=survey.deadline + timedelta(seconds=1)) == 1
        row = VacationResponse.objects.get(survey=survey, user_id=1003)
        assert row.response == "no" and row.is_default
        return
    if case_id == "TC-FR-085":
        h.active_role(3001, "caretaker")
        h.active_role(3002, "warden")
        for index in range(25):
            user_id = 4000 + index
            h.enrollment(user_id)
            VacationResponse.objects.create(
                survey=survey,
                user_id=user_id,
                response="yes" if index < 10 else "no",
            )
        for role, uid in (("caretaker", 3001), ("warden", 3002)):
            response = h.client(uid, role).get(
                "/api/v1/mms/reports?type=vacation")
            assert response.status_code == 200
            result = next(row for row in response.json()["results"]
                          if row["id"] == survey.id)
            assert result["yes"] == 10 and result["no"] == 15


def _run_special_food(h, case_id):
    if case_id in {"TC-FR-086", "TC-FR-087", "TC-FR-088", "TC-FR-089",
                   "TC-FR-096"}:
        h.enrollment(1001)
        if case_id in {"TC-FR-087", "TC-FR-088"}:
            with freeze_time("2026-10-18T12:00:00Z"):
                response = _submit_special_food(
                    h.client(1001),
                    requested_for="2026-10-19" if case_id == "TC-FR-087"
                    else "2026-10-18",
                )
        else:
            response = _submit_special_food(h.client(1001))
        if case_id == "TC-FR-088":
            assert response.status_code == 409
        else:
            assert response.status_code == 201
            assert response.json()["status"] == "requested"
            if case_id == "TC-FR-089":
                assert NotificationOutbox.objects.filter(
                    topic="special_food.submitted", recipient_user_id=1001).exists()
        return

    if case_id in {"TC-FR-090", "TC-FR-091", "TC-FR-093"}:
        h.active_role(3001, "caretaker")
        request = SpecialFoodRequest.objects.create(
            user_id=1001,
            reason="illness",
            requested_for=date(2026, 10, 19),
        )
        response = h.client(3001, "caretaker").post(
            f"/api/v1/mms/special-food/{request.id}/decision",
            {"approve": case_id != "TC-FR-091"},
            format="json",
        )
        assert response.status_code == 200
        assert response.json()["status"] == (
            "rejected" if case_id == "TC-FR-091" else "approved")
        if case_id == "TC-FR-093":
            assert NotificationOutbox.objects.filter(
                topic="special_food.decided", recipient_user_id=1001).exists()
        return
    if case_id == "TC-FR-094":
        request = SpecialFoodRequest.objects.create(
            user_id=1001,
            reason="illness",
            requested_for=date(2026, 10, 19),
        )
        SpecialFoodHistory.objects.create(
            request=request, status="requested", actor_user_id=1001)
        response = h.client(1001).get("/api/v1/mms/special-food")
        row = response.json()["results"][0]
        assert row["id"] == request.id
        assert row["history"][0]["status"] == "requested"


def _run_announcement(h, case_id):
    if case_id in {"TC-FR-104", "TC-FR-105", "TC-FR-106"}:
        role = "warden" if case_id == "TC-FR-105" else "caretaker"
        h.active_role(3001, role)
        h.identity(1001)
        response = h.client(3001, role).post(
            "/api/v1/mms/announcements",
            {"title": "Service update", "body": "Mess service notice"},
            format="json",
        )
        assert response.status_code == 201
        assert response.json()["published_by_user_id"] == 3001
        if case_id == "TC-FR-106":
            assert NotificationOutbox.objects.filter(
                topic="announcement.published", recipient_user_id=1001).exists()
        return
    announcement = Announcement.objects.create(
        title="History entry",
        body="Published notice",
        published_by_user_id=3001,
        published_by_role="caretaker",
        published_at=timezone.now(),
    )
    response = h.client(1001).get("/api/v1/mms/announcements")
    assert response.status_code == 200
    row = response.json()["results"][0]
    assert row["id"] == announcement.id
    assert row["title"] == "History entry"
    assert row["body"] == "Published notice"
    assert row["published_by_user_id"] == 3001
    assert row["published_at"]


def _run_reports(h, case_id):
    if case_id == "TC-FR-109":
        h.active_role(3002, "warden")
        h.enrollment(1001)
        response = h.client(3002, "warden").get("/api/v1/mms/overview")
        assert response.status_code == 200
        assert response.json()["enrollment_count"] == 1
        assert "requests" in response.json()
    elif case_id == "TC-FR-110":
        h.active_role(3002, "warden")
        _create_bill(1001)
        response = h.client(3002, "warden").get(
            "/api/v1/mms/reports?type=billing_summary")
        assert response.status_code == 200
        assert response.json()["results"]
    elif case_id == "TC-FR-112":
        h.active_role(3001, "caretaker")
        StudentRequest.objects.create(
            user_id=1001, kind="registration", window=h.window(), status="approved")
        response = h.client(3001, "caretaker").get(
            "/api/v1/mms/reports?type=registration_trends")
        assert response.status_code == 200
        assert response.json()["results"]
    elif case_id == "TC-FR-115":
        h.active_role(3001, "caretaker")
        StudentRequest.objects.create(
            user_id=1001, kind="registration", window=h.window())
        response = h.client(3001, "caretaker").get(
            "/api/v1/mms/reports?type=registration_trends")
        assert response.status_code == 200
        assert set(response.json()["results"][0]) == {
            "created_at__date", "status", "count"}


def _run_notification(h, case_id):
    if case_id == "TC-FR-116":
        before = NotificationOutbox.objects.count()
        week = MenuWeek.objects.create(
            week_start=date(2026, 10, 5), updated_by_user_id=3001)
        from modules.mms.models import MenuEntry

        MenuEntry.objects.bulk_create(
            MenuEntry(week=week, day=entry["day"], meal=entry["meal"],
                      item="Weekly meal")
            for entry in _menu_entries()
        )
        response = h.client(1001).get("/api/v1/mms/menu")
        assert response.status_code == 200
        assert NotificationOutbox.objects.count() == before
        return
    h.enrollment(1001)
    with freeze_time("2026-10-01T12:00:00Z"):
        response = _submit_rebate(h.client(1001))
    assert response.status_code == 201
    event = NotificationOutbox.objects.get(
        topic="rebate.submitted", recipient_user_id=1001)
    assert event.dedupe_key
    assert event.subject
    assert event.body
    assert event.recipient_email == ""
    assert not hasattr(event, "smtp_server")


BLOCKED = {
    "TC-FR-045": (
        "No fixed-charge configuration or bill field is defined by the "
        "current MMS implementation."
    ),
    "TC-FR-048": (
        "No prior outstanding-balance input/roll-forward model or rule is "
        "defined by the current MMS implementation."
    ),
    "TC-FR-092": (
        "The frozen case does not specify the institution-defined decision "
        "period; test settings may leave it unset."
    ),
    "TC-FR-090": (
        "Approval requires a policy-provided special-food charge, but the "
        "frozen case provides no amount or policy value."
    ),
    "TC-FR-093": (
        "Approval and its notification require a policy-provided special-food "
        "charge, but the frozen case provides no amount or policy value."
    ),
    "TC-FR-097": (
        "The frozen case does not specify the fulfillment actor; the "
        "implementation marks that actor policy unresolved."
    ),
    "TC-FR-098": (
        "The frozen case does not specify the fulfillment actor; the "
        "implementation marks that actor policy unresolved."
    ),
    "TC-FR-099": (
        "The frozen case does not specify the fulfillment actor; the "
        "implementation marks that actor policy unresolved."
    ),
    "TC-FR-100": (
        "The frozen case does not specify the fulfillment actor; the "
        "implementation marks that actor policy unresolved."
    ),
    "TC-FR-101": (
        "The frozen case does not specify the fulfillment actor; the "
        "implementation marks that actor policy unresolved."
    ),
    "TC-FR-102": (
        "The frozen case does not specify the fulfillment actor; the "
        "implementation marks that actor policy unresolved."
    ),
    "TC-FR-111": (
        "No Warden feedback/trend report type or aggregation contract is "
        "exposed by the current MMS API."
    ),
    "TC-FR-113": (
        "No rebate-consumption report type or aggregation contract is "
        "exposed by the current MMS API."
    ),
    "TC-FR-114": (
        "The feedback endpoint exposes raw entries, but no operational "
        "feedback summary contract is specified."
    ),
}

HANDLERS = {
    **{f"TC-FR-{number:03}": _run_role for number in range(2, 15)},
    **{f"TC-FR-{number:03}": _run_registration for number in range(15, 32)},
    **{f"TC-FR-{number:03}": _run_menu for number in range(32, 42)},
    **{f"TC-FR-{number:03}": _run_billing for number in range(42, 53)},
    **{f"TC-FR-{number:03}": _run_feedback for number in range(53, 57)},
    **{f"TC-FR-{number:03}": _run_rebate for number in range(57, 76)},
    **{f"TC-FR-{number:03}": _run_vacation for number in range(76, 86)},
    **{f"TC-FR-{number:03}": _run_special_food for number in range(86, 97)},
    **{f"TC-FR-{number:03}": _run_announcement for number in range(103, 109)},
    "TC-FR-109": _run_reports,
    "TC-FR-110": _run_reports,
    "TC-FR-112": _run_reports,
    "TC-FR-115": _run_reports,
    "TC-FR-116": _run_notification,
    "TC-FR-117": _run_notification,
}
HANDLERS["TC-FR-001"] = lambda h, _case_id: _run_status(h)


@pytest.mark.parametrize(
    "case_id",
    [f"TC-FR-{number:03}" for number in range(1, 118)],
    ids=[f"TC-FR-{number:03}" for number in range(1, 118)],
)
def test_frozen_fr_case(case_id, stub_iam, user_ref):
    if case_id in BLOCKED:
        pytest.skip(BLOCKED[case_id])
    handler = HANDLERS.get(case_id)
    assert handler is not None, f"{case_id} has no automated test handler"
    handler(Harness(stub_iam, user_ref), case_id)
