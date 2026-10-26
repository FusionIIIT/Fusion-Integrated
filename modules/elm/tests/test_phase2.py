"""Regression tests tied to the supplied synchronized ELM baseline."""

from datetime import date
from decimal import Decimal

import pytest
from freezegun import freeze_time
from rest_framework.test import APIClient

from conftest import make_principal, make_session
from core.api.exceptions import ConflictError, DomainError, PermissionDeniedError
from modules.elm.domain.state_machine import count_days
from modules.elm.models import (
    AccountEntry,
    AttendanceEvent,
    EmployeeRecord,
    HolidayCalendar,
    LeaveBalance,
    LeavePolicy,
    LeaveRequest,
    VacationPeriod,
)
from modules.elm.services.leave_service import LeaveService, account
from modules.elm.services.scheduled import close_year, process_sla

pytestmark = [pytest.mark.django_db]
PERMS = (
    "elm.leave.apply",
    "elm.leave.view_self",
    "elm.leave.substitute",
    "elm.leave.approve",
    "elm.leave.admin",
)


def actor(uid=1, role="staff", permissions=PERMS, kind="staff", modules=("elm",)):
    return make_principal(
        user_id=uid,
        kind=kind,
        roles=(role,),
        active_role=role,
        permissions=permissions,
        modules=modules,
    )


@pytest.fixture(autouse=True)
def time_now():
    with freeze_time("2026-10-26 08:00:00"):
        yield


@pytest.fixture
def profiles():
    route = {
        c: [{"user_id": "2", "role": "unit_head"}]
        + ([] if c in {"CL", "RH"} else [{"user_id": "3", "role": "director"}])
        for c in ["CL", "RH", "SCL", "EL", "COL", "VL"]
    }
    for uid in range(1, 7):
        EmployeeRecord.objects.create(
            user_id=str(uid),
            kind="faculty" if uid == 5 else "staff",
            unit="CSE",
            designation="Employee",
            routes=route,
        )
    HolidayCalendar.objects.create(
        year=2026,
        restricted_dates=["2026-10-27"],
        closed_dates=["2026-10-28"],
        published_at="2026-01-01T00:00:00Z",
    )
    HolidayCalendar.objects.create(
        year=2027, restricted_dates=[], closed_dates=[], published_at="2026-01-01T00:00:00Z"
    )
    return EmployeeRecord.objects.get(pk="1")


def apply(category="CL", start="2026-10-27", end="2026-10-27", who=None, **kw):
    return LeaveService.apply_leave(
        who or actor(),
        leave_type=category,
        start_date=date.fromisoformat(start),
        end_date=date.fromisoformat(end),
        reason="Family commitment",
        **kw,
    )


def approve(req, yes=True, note=""):
    step = req.route[req.route_index]
    return LeaveService.review_unit_head(
        actor(int(step["user_id"]), step["role"]), req.pk, yes, note
    )


@pytest.mark.parametrize(
    "category,expected",
    [("CL", "8"), ("RH", "2"), ("SCL", "15"), ("EL", "30"), ("COL", "20"), ("VL", "0")],
)
def test_staff_entitlements(profiles, category, expected):
    assert account(profiles, category, 2026).balance == Decimal(expected)


@pytest.mark.parametrize("category,expected", [("EL", "0"), ("VL", "60")])
def test_faculty_entitlements(profiles, category, expected):
    assert account(EmployeeRecord.objects.get(pk="5"), category, 2026).balance == Decimal(expected)


@pytest.mark.parametrize(
    "category,expected", [("EL", 3), ("COL", 3), ("VL", 3), ("CL", 1), ("SCL", 1)]
)
def test_continuous_counting(category, expected):
    assert count_days(category, date(2026, 10, 30), date(2026, 11, 1)) == expected


@pytest.mark.parametrize(
    "kwargs",
    [
        {"leave_type": "BAD"},
        {"duration_days": Decimal("0")},
        {"duration_days": Decimal("7")},
        {"is_half_day": True, "half_day_session": "BAD"},
    ],
)
def test_invalid_requests_leave_no_reservation(profiles, kwargs):
    category = kwargs.pop("leave_type", "CL")
    with pytest.raises(DomainError):
        apply(category, **kwargs)
    assert LeaveRequest.objects.count() == 0
    assert AccountEntry.objects.count() == 0


def test_half_days_nonoverlap(profiles):
    apply(is_half_day=True, half_day_session="FN")
    apply(is_half_day=True, half_day_session="AN")
    with pytest.raises(ConflictError):
        apply(is_half_day=True, half_day_session="FN")
    assert LeaveBalance.objects.get(user_id="1", leave_type="CL").pending == 1


def test_full_day_overlaps_half(profiles):
    apply(is_half_day=True, half_day_session="FN")
    with pytest.raises(ConflictError):
        apply()


def test_reversed_dates(profiles):
    with pytest.raises(DomainError):
        apply(start="2026-10-29", end="2026-10-27")


def test_calendar_required(profiles):
    HolidayCalendar.objects.all().delete()
    with pytest.raises(DomainError, match="calendar"):
        apply()


def test_draft_calendar_does_not_replace_published(profiles):
    HolidayCalendar.objects.create(year=2026, restricted_dates=["2026-10-29"])
    apply("RH")
    with pytest.raises(DomainError):
        apply("RH", start="2026-10-29", end="2026-10-29")


def test_vacation_calendar_required(profiles):
    with pytest.raises(DomainError, match="vacation"):
        apply("VL", who=actor(5, "faculty", kind="faculty"))
    VacationPeriod.objects.create(
        start_date=date(2026, 10, 26),
        end_date=date(2026, 11, 1),
        source_reference="Published academic calendar",
    )
    assert apply("VL", who=actor(5, "faculty", kind="faculty")).duration_days == 1


def test_staff_cannot_use_vacation(profiles):
    with pytest.raises(DomainError):
        apply("VL")


def test_col_evidence(profiles):
    LeavePolicy.objects.create(medical_evidence_required=True)
    with pytest.raises(DomainError, match="evidence"):
        apply("COL")
    apply("COL", evidence_reference="Medical certificate 01")


def test_station_details(profiles):
    with pytest.raises(DomainError, match="Station"):
        apply(station_leave=True)
    assert apply(
        station_leave=True,
        station_leave_address="Bhopal",
        out_of_station_from=date(2026, 10, 26),
        out_of_station_to=date(2026, 10, 28),
    ).station_leave


def test_substitute_self_or_unknown(profiles):
    for sub in ["1", "999"]:
        with pytest.raises(DomainError):
            apply(substitute_id=sub)


def test_substitute_conflict(profiles):
    apply(who=actor(4))
    with pytest.raises(ConflictError):
        apply(substitute_id="4")


def test_required_substitute(profiles):
    profiles.coverage_required = True
    profiles.save()
    with pytest.raises(DomainError, match="substitute"):
        apply()


def test_decline_replacement_and_accept(profiles):
    req = apply(substitute_id="4")
    req = LeaveService.respond_substitute(actor(4), req.pk, False, "Unavailable")
    assert req.status == "APPLICANT_ACTION"
    assert LeaveBalance.objects.get(user_id="1", leave_type="CL").pending == 1
    req = LeaveService.replace_substitute(actor(), req.pk, "6")
    req = LeaveService.respond_substitute(actor(6), req.pk, True)
    assert req.status == "PENDING_UNIT_HEAD"
    assert req.current_approver_user_id == "2"


def test_consent_blocks_approval(profiles):
    req = apply(substitute_id="4")
    with pytest.raises(ConflictError):
        LeaveService.review_unit_head(actor(2, "unit_head"), req.pk, True)


def test_accept_responsibility_blocks_new_leave(profiles):
    req = apply(substitute_id="4")
    LeaveService.respond_substitute(actor(4), req.pk, True)
    with pytest.raises(ConflictError):
        apply(who=actor(4))


def test_wrong_approver_and_role(profiles):
    req = apply()
    for who in [actor(3, "unit_head"), actor(2, "staff"), actor()]:
        with pytest.raises(PermissionDeniedError):
            LeaveService.review_unit_head(who, req.pk, True)


def test_not_recommended_still_routes(profiles):
    req = apply("EL")
    req = approve(req, False, "Operational concern")
    assert req.status == "PENDING_AUTHORITY"
    assert req.recommendation == "NOT_RECOMMENDED"
    req = approve(req)
    assert req.status == "APPROVED"
    b = LeaveBalance.objects.get(user_id="1", leave_type="EL")
    assert b.availed == 1 and b.pending == 0
    assert AttendanceEvent.objects.filter(request=req, event="APPROVED").exists()


def test_director_self_sanction(profiles):
    p = EmployeeRecord.objects.get(pk="3")
    p.is_director = True
    p.save()
    req = apply(who=actor(3, "director"))
    assert req.current_approver_user_id == "3"
    assert approve(req).status == "APPROVED"


def test_withdraw_terminal_and_idempotent_balance(profiles):
    req = apply()
    LeaveService.withdraw_leave(actor(), req.pk, "Plans changed")
    with pytest.raises(ConflictError):
        approve(req)
    with pytest.raises(ConflictError):
        LeaveService.withdraw_leave(actor(), req.pk)
    assert LeaveBalance.objects.get(user_id="1", leave_type="CL").pending == 0


def test_withdraw_other_person_denied(profiles):
    req = apply()
    with pytest.raises(PermissionDeniedError):
        LeaveService.withdraw_leave(actor(4), req.pk)


@pytest.mark.parametrize("cancel_approved", [True, False])
def test_cancellation_same_route_and_balance(profiles, cancel_approved):
    original = approve(apply())
    with pytest.raises(ConflictError):
        LeaveService.withdraw_leave(actor(), original.pk)
    req = LeaveService.followup(actor(), original.pk, "CANCEL", reason="Plans changed")
    assert req.route == original.route
    approve(req, cancel_approved, "Decision")
    original.refresh_from_db()
    assert original.status == ("CANCELLED" if cancel_approved else "APPROVED")
    assert LeaveBalance.objects.get(user_id="1", leave_type="CL").availed == (
        0 if cancel_approved else 1
    )


def test_cancellation_after_start_denied(profiles):
    original = approve(apply(start="2026-10-26", end="2026-10-26"))
    with pytest.raises(ConflictError):
        LeaveService.followup(actor(), original.pk, "CANCEL", reason="Too late")


def ongoing_el():
    with freeze_time("2026-10-20"):
        req = apply("EL", start="2026-10-24", end="2026-10-28")
        req = approve(req)
        return approve(req)


def test_extension_incremental_only(profiles):
    original = ongoing_el()
    req = LeaveService.followup(
        actor(), original.pk, "EXTEND", end_date=date(2026, 10, 30), reason="Need two days"
    )
    assert req.start_date == date(2026, 10, 29) and req.duration_days == 2
    req = approve(req)
    approve(req)
    original.refresh_from_db()
    assert original.end_date == date(2026, 10, 28)
    assert LeaveBalance.objects.get(user_id="1", leave_type="EL").availed == 7


@pytest.mark.parametrize(
    "actual,expected", [("2026-10-26", 3), ("2026-10-28", 5), ("2026-10-30", 7)]
)
def test_early_normal_late_resumption(profiles, actual, expected):
    original = ongoing_el()
    with freeze_time("2026-10-31"):
        req = LeaveService.followup(
            actor(),
            original.pk,
            "RESUME",
            end_date=date.fromisoformat(actual),
            reason="Returned to duty",
        )
        assert req.current_approver_user_id == "3"
        approve(req)
        original.refresh_from_db()
        assert original.end_date == date(2026, 10, 28)
        assert original.actual_end_date == date.fromisoformat(actual)
        assert LeaveBalance.objects.get(user_id="1", leave_type="EL").availed == expected
        assert AttendanceEvent.objects.filter(event="RESUMPTION_REVIEWED").count() == 1


def test_year_end_fractional_conversion_idempotent(profiles):
    faculty = EmployeeRecord.objects.get(pk="5")
    b = account(faculty, "VL", 2026)
    b.availed = Decimal("1")
    b.save()
    with freeze_time("2027-01-01"):
        assert not close_year(2026)["exceptions"]
        assert LeaveBalance.objects.get(
            user_id="5", leave_type="EL", year=2027
        ).credited == Decimal("29.5")
        assert not close_year(2026)["processed"]
        assert LeaveBalance.objects.get(
            user_id="5", leave_type="EL", year=2027
        ).credited == Decimal("29.5")


def test_year_end_pending_exception(profiles):
    apply()
    with freeze_time("2027-01-01"):
        report = close_year(2026)
    assert any(e["user_id"] == "1" for e in report["exceptions"])
    assert not LeaveBalance.objects.get(user_id="1", leave_type="CL", year=2026).closed


def test_sla_only_pending_idempotent(profiles):
    req = apply()
    with freeze_time("2026-10-29"):
        assert process_sla() == {"reminders": 1, "escalations": 1}
        assert process_sla() == {"reminders": 0, "escalations": 0}
        approve(req)
        assert process_sla() == {"reminders": 0, "escalations": 0}


def test_offline_sync_no_new_workflow(profiles):
    req = LeaveService.record_offline(
        actor(6, "leave_admin"),
        "1",
        "Sanction/2026/12",
        "Server unavailable",
        leave_type="CL",
        start_date=date(2026, 10, 20),
        end_date=date(2026, 10, 20),
        reason="Medical appointment",
    )
    assert req.status == "APPROVED" and req.current_approver_user_id == ""
    assert LeaveBalance.objects.get(user_id="1", leave_type="CL").availed == 1


@pytest.fixture
def api(stub_iam):
    def make(uid=1, role="staff", permissions=PERMS, modules=("elm",)):
        stub_iam(
            session=make_session(
                user_id=uid,
                kind="staff",
                roles=(role,),
                active_role=role,
                permissions=permissions,
                modules=modules,
            )
        )
        c = APIClient()
        c.credentials(HTTP_AUTHORIZATION="Token test-session")
        return c

    return make


@pytest.mark.parametrize(
    "url",
    [
        "leaves/",
        "balances/",
        "approvals/",
        "substitute-queue/",
        "admin/policy/",
        "admin/employees/",
    ],
)
def test_api_module_gate(profiles, api, url):
    assert api(modules=()).get("/api/v1/elm/" + url).status_code == 403


def test_api_anonymous_gate(profiles):
    assert APIClient().get("/api/v1/elm/leaves/").status_code == 401


def test_api_permission_gate(profiles, api):
    assert api(permissions=()).post("/api/v1/elm/leaves/", {}, format="json").status_code == 403


def test_api_numeric_identity_and_error_envelope(profiles, api):
    c = api()
    response = c.post(
        "/api/v1/elm/leaves/",
        {
            "leave_type": "CL",
            "start_date": "2026-10-27",
            "end_date": "2026-10-27",
            "reason": "Appointment",
        },
        format="json",
    )
    assert response.status_code == 201, response.data
    assert response.data["applicant_user_id"] == "1"
    response = c.post("/api/v1/elm/leaves/", {"leave_type": "BAD"}, format="json")
    assert response.status_code == 400 and "message" in response.data["error"]


def test_api_approval_queue_is_assigned_only(profiles, api):
    apply()
    assert len(api(2, "unit_head").get("/api/v1/elm/approvals/").data) == 1
    assert api(3, "unit_head").get("/api/v1/elm/approvals/").data == []


def test_api_export_owner_only_escaped(profiles, api):
    req = apply()
    req.reason = "<script>alert(1)</script>"
    req.save()
    r = api().get(f"/api/v1/elm/leaves/{req.pk}/export/")
    assert r.status_code == 200 and b"&lt;script&gt;" in r.content
    assert api(4).get(f"/api/v1/elm/leaves/{req.pk}/export/").status_code == 404


def test_maintenance_cannot_sanction(profiles, api):
    req = apply()
    c = api(6, "leave_admin")
    assert (
        c.post(
            f"/api/v1/elm/leaves/{req.pk}/maintenance/", {"status": "APPROVED"}, format="json"
        ).status_code
        == 422
    )
    assert (
        c.post(
            f"/api/v1/elm/leaves/{req.pk}/maintenance/",
            {"remarks": "Reference verified"},
            format="json",
        ).status_code
        == 200
    )
    req.refresh_from_db()
    assert req.status == "PENDING_UNIT_HEAD"


def test_config_sla_validation(profiles, api):
    c = api(6, "leave_admin")
    assert (
        c.post(
            "/api/v1/elm/admin/policy/",
            {"reminder_hours": 48, "escalation_hours": 24},
            format="json",
        ).status_code
        == 400
    )


def test_missing_request_is_404(profiles, api):
    response = api().post(
        "/api/v1/elm/leaves/00000000-0000-0000-0000-000000000001/withdraw/",
        {"reason": "No longer needed"},
        format="json",
    )
    assert response.status_code == 404


def test_early_resumption_releases_approved_extension_dates(profiles):
    original = ongoing_el()
    ext = LeaveService.followup(
        actor(), original.pk, "EXTEND", end_date=date(2026, 10, 30), reason="Additional time"
    )
    approve(approve(ext))
    with freeze_time("2026-10-29"):
        resume = LeaveService.followup(
            actor(), original.pk, "RESUME", end_date=date(2026, 10, 26), reason="Returned early"
        )
        approve(resume)
        # Oct 30 was in the extension but is free again after reviewed early return.
        assert apply(start="2026-10-30", end="2026-10-30").status == "PENDING_UNIT_HEAD"


def test_late_resumption_blocks_new_overlap_beyond_original_end(profiles):
    original = ongoing_el()
    with freeze_time("2026-10-31"):
        resume = LeaveService.followup(
            actor(), original.pk, "RESUME", end_date=date(2026, 10, 30), reason="Returned later"
        )
        approve(resume)
        from modules.elm.services.leave_service import overlaps

        assert overlaps("1", date(2026, 10, 30), date(2026, 10, 30))


def test_zero_duration_cannot_be_persisted(profiles):
    from django.db import IntegrityError, transaction

    with pytest.raises(IntegrityError), transaction.atomic():
        LeaveRequest.objects.create(
            applicant_user_id="1",
            leave_type="CL",
            start_date=date(2026, 10, 27),
            end_date=date(2026, 10, 27),
            duration_days=0,
            reason="Invalid",
        )


def test_year_end_does_not_close_pending_resumption(profiles):
    original = ongoing_el()
    with freeze_time("2026-10-31"):
        LeaveService.followup(
            actor(), original.pk, "RESUME", end_date=date(2026, 10, 28), reason="Returned"
        )
    with freeze_time("2027-01-01"):
        assert any(e["user_id"] == "1" for e in close_year(2026)["exceptions"])
