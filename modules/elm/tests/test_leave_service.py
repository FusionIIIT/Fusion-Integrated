"""Integration tests for ELM services, selectors, and cross-module contracts."""

from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.http import Http404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from modules.elm.contracts import get_employee_leave_profiles
from modules.elm.models import LeaveBalance
from modules.elm.selectors.queries import list_approval_queue, list_employee_applications
from modules.elm.services.leave import (
    allot_balance,
    cancel_approved,
    decide,
    record_offline_leave,
    replace_substitute,
    request_cancellation,
    request_extension,
    review_resumption,
    rollover_balances,
    submit,
    submit_resumption,
    upsert_holiday,
    upsert_profile,
    withdraw,
)


def _principal(user_id: int, permissions: set[str] | None = None) -> SimpleNamespace:
    perms = (
        set(permissions)
        if permissions is not None
        else {
            "leave_elm.application.view",
            "leave_elm.application.apply",
            "leave_elm.application.approve",
            "leave_elm.balance.view",
        }
    )
    return SimpleNamespace(
        user_id=user_id,
        has_permission=lambda code: code in perms,
        has_any_permission=lambda *codes: bool(set(codes) & perms),
        has_module=lambda m: m == "leave_elm",
    )


@pytest.mark.django_db
def test_cl_submission_and_unit_head_final_approval():
    upsert_profile(
        {
            "user_id": 101,
            "category": "staff",
            "designation": "Senior Assistant",
            "unit": "Establishment",
            "unit_head_user_id": 201,
            "sanction_authority_user_id": 301,
        }
    )
    allot_balance(
        {"employee_id": 101, "category": "CL", "year": 2026, "allotted": Decimal("8.0")}
    )
    app = submit(
        _principal(101),
        {
            "category": "CL",
            "start_date": date(2026, 10, 12),
            "end_date": date(2026, 10, 12),
            "half_day": "FIRST",
            "reason": "Personal work",
        },
    )
    assert app.status == "PENDING"
    assert app.duration == Decimal("0.5")
    with pytest.raises(PermissionDenied):
        decide(_principal(101), app.id, action="approve")
    decided = decide(_principal(201), app.id, action="approve", remarks="Approved")
    assert decided.status == "APPROVED"
    bal = LeaveBalance.objects.get(employee_id=101, year=2026, category="CL")
    assert bal.used == Decimal("0.5")


@pytest.mark.django_db
def test_el_substitute_recommendation_and_higher_sanction():
    upsert_profile(
        {
            "user_id": 102,
            "category": "faculty",
            "designation": "Assistant Professor",
            "unit": "CSE",
            "unit_head_user_id": 202,
            "sanction_authority_user_id": 302,
        }
    )
    upsert_profile(
        {
            "user_id": 103,
            "category": "faculty",
            "designation": "Assistant Professor",
            "unit": "CSE",
            "unit_head_user_id": 202,
            "sanction_authority_user_id": 302,
        }
    )
    allot_balance(
        {"employee_id": 102, "category": "EL", "year": 2026, "allotted": Decimal("30.0")}
    )
    app = submit(
        _principal(102),
        {
            "category": "EL",
            "start_date": date(2026, 11, 2),
            "end_date": date(2026, 11, 4),
            "reason": "Family event",
            "station_leave": True,
            "station_location": "Delhi",
            "substitute_user_id": 103,
        },
    )
    assert app.status == "AWAITING_SUB"
    assert list(list_approval_queue(103)) == [app]
    sub_ok = decide(_principal(103), app.id, action="accept_substitute", remarks="Will cover")
    assert sub_ok.status == "PENDING"
    rec = decide(_principal(202), app.id, action="recommend", remarks="Forwarded")
    assert rec.status == "RECOMMENDED"
    assert rec.recommendation == "RECOMMENDED"
    final = decide(_principal(302), app.id, action="approve", remarks="Sanctioned")
    assert final.status == "APPROVED"
    bal = LeaveBalance.objects.get(employee_id=102, year=2026, category="EL")
    assert bal.used == Decimal("3.0")


@pytest.mark.django_db
def test_withdrawal_and_pre_start_cancellation():
    upsert_profile(
        {
            "user_id": 104,
            "category": "faculty",
            "designation": "Associate Professor",
            "unit": "ECE",
            "unit_head_user_id": 204,
            "sanction_authority_user_id": 304,
        }
    )
    future_day = date.today() + timedelta(days=30)
    while future_day.weekday() >= 5:
        future_day += timedelta(days=1)
    allot_balance(
        {
            "employee_id": 104,
            "category": "RH",
            "year": future_day.year,
            "allotted": Decimal("2.0"),
        }
    )
    upsert_holiday({"date": future_day, "name": "Festival RH", "kind": "RH", "published": True})
    pending = submit(
        _principal(104),
        {
            "category": "RH",
            "start_date": future_day,
            "end_date": future_day,
            "reason": "Observance",
        },
    )
    withdrawn = withdraw(_principal(104), pending.id)
    assert withdrawn.status == "WITHDRAWN"

    second = submit(
        _principal(104),
        {
            "category": "RH",
            "start_date": future_day,
            "end_date": future_day,
            "reason": "Re-applied",
        },
    )
    decide(_principal(204), second.id, action="approve")
    cancel_req = cancel_approved(_principal(104), second.id, remarks="Plans changed")
    assert cancel_req.status == "AWAITING_CANCEL"
    bal_mid = LeaveBalance.objects.get(employee_id=104, year=future_day.year, category="RH")
    assert bal_mid.used == Decimal("1.0")

    cancelled = decide(
        _principal(204), second.id, action="approve_cancellation", remarks="Approved cancellation"
    )
    assert cancelled.status == "CANCELLED"
    bal = LeaveBalance.objects.get(employee_id=104, year=future_day.year, category="RH")
    assert bal.used == Decimal("0.0")
    assert len(list_employee_applications(104)) == 2
    assert get_employee_leave_profiles([104])[0]["unit"] == "ECE"


@pytest.mark.django_db
def test_validation_guards_station_leave_and_overlap():
    upsert_profile(
        {
            "user_id": 105,
            "category": "staff",
            "designation": "Clerk",
            "unit": "Admin",
            "unit_head_user_id": 205,
            "sanction_authority_user_id": 305,
        }
    )
    allot_balance(
        {"employee_id": 105, "category": "CL", "year": 2026, "allotted": Decimal("8.0")}
    )
    with pytest.raises(ValidationError):
        submit(
            _principal(105),
            {
                "category": "CL",
                "start_date": date(2026, 10, 12),
                "end_date": date(2026, 10, 12),
                "reason": "Trip",
                "station_leave": True,
                "station_location": "",
            },
        )
    submit(
        _principal(105),
        {
            "category": "CL",
            "start_date": date(2026, 10, 12),
            "end_date": date(2026, 10, 13),
            "reason": "First request",
        },
    )
    with pytest.raises(ValidationError):
        submit(
            _principal(105),
            {
                "category": "CL",
                "start_date": date(2026, 10, 13),
                "end_date": date(2026, 10, 14),
                "reason": "Overlapping request",
            },
        )


@pytest.mark.django_db
def test_substitute_overlap_and_eligibility_validation():
    upsert_profile(
        {
            "user_id": 110,
            "category": "staff",
            "designation": "Assistant",
            "unit": "Accounts",
            "unit_head_user_id": 210,
            "sanction_authority_user_id": 310,
        }
    )
    upsert_profile(
        {
            "user_id": 111,
            "category": "staff",
            "designation": "Clerk",
            "unit": "Accounts",
            "unit_head_user_id": 210,
            "sanction_authority_user_id": 310,
        }
    )
    allot_balance(
        {"employee_id": 110, "category": "CL", "year": 2026, "allotted": Decimal("8.0")}
    )
    allot_balance(
        {"employee_id": 111, "category": "CL", "year": 2026, "allotted": Decimal("8.0")}
    )

    with pytest.raises(ValidationError) as exc:
        submit(
            _principal(110),
            {
                "category": "CL",
                "start_date": date(2026, 10, 12),
                "end_date": date(2026, 10, 13),
                "reason": "Family work",
                "substitute_user_id": 99999,
            },
        )
    assert "Nominated substitute must be an active employee." in str(exc.value)

    sub_leave = submit(
        _principal(111),
        {
            "category": "CL",
            "start_date": date(2026, 10, 12),
            "end_date": date(2026, 10, 14),
            "reason": "Personal",
        },
    )

    with pytest.raises(ValidationError) as exc:
        submit(
            _principal(110),
            {
                "category": "CL",
                "start_date": date(2026, 10, 14),
                "end_date": date(2026, 10, 16),
                "reason": "Holiday",
                "substitute_user_id": 111,
            },
        )
    assert "Nominated substitute has overlapping leave." in str(exc.value)

    valid_app = submit(
        _principal(110),
        {
            "category": "CL",
            "start_date": date(2026, 10, 15),
            "end_date": date(2026, 10, 16),
            "reason": "Holiday",
            "substitute_user_id": 111,
        },
    )
    assert valid_app.status == "AWAITING_SUB"

    withdraw(_principal(111), sub_leave.id)
    withdrawn_overlap_ok = submit(
        _principal(110),
        {
            "category": "CL",
            "start_date": date(2026, 10, 12),
            "end_date": date(2026, 10, 14),
            "reason": "Emergency",
            "substitute_user_id": 111,
        },
    )
    assert withdrawn_overlap_ok.status == "AWAITING_SUB"


@pytest.mark.django_db
def test_director_self_sanction_service_workflow():
    upsert_profile(
        {
            "user_id": 501,
            "category": "faculty",
            "designation": "Director",
            "unit": "Administration",
            "unit_head_user_id": None,
            "sanction_authority_user_id": None,
        }
    )
    upsert_profile(
        {
            "user_id": 502,
            "category": "faculty",
            "designation": "Dean",
            "unit": "Academic",
            "unit_head_user_id": 501,
            "sanction_authority_user_id": 501,
        }
    )
    allot_balance(
        {"employee_id": 501, "category": "EL", "year": 2026, "allotted": Decimal("30.0")}
    )
    allot_balance(
        {"employee_id": 502, "category": "EL", "year": 2026, "allotted": Decimal("30.0")}
    )

    dir_app = submit(
        _principal(501),
        {
            "category": "EL",
            "start_date": date(2026, 11, 2),
            "end_date": date(2026, 11, 4),
            "reason": "Official visit",
        },
    )
    assert dir_app.status == "PENDING"
    assert dir_app.sanction_authority_id == 501

    dean_app = submit(
        _principal(502),
        {
            "category": "EL",
            "start_date": date(2026, 11, 2),
            "end_date": date(2026, 11, 4),
            "reason": "Personal",
        },
    )
    with pytest.raises(PermissionDenied, match=r"applicant cannot decide their own leave"):
        decide(_principal(502), dean_app.id, action="approve")

    with pytest.raises(PermissionDenied, match=r"Only the Director can self-sanction this leave"):
        decide(_principal(502), dir_app.id, action="approve")

    with pytest.raises(ValidationError) as exc:
        decide(_principal(501), dir_app.id, action="recommend")
    assert "Director self-sanction must be approve or reject." in str(exc.value)

    decided = decide(_principal(501), dir_app.id, action="approve", remarks="Approved by Director")
    assert decided.status == "APPROVED"
    assert decided.approver_id == 501
    bal = LeaveBalance.objects.get(employee_id=501, category="EL", year=2026)
    assert bal.used == Decimal("3.0")


@pytest.mark.django_db
def test_approved_leave_cancellation_workflow_and_boundaries():
    upsert_profile(
        {
            "user_id": 601,
            "category": "staff",
            "designation": "Assistant",
            "unit": "Finance",
            "unit_head_user_id": 602,
            "sanction_authority_user_id": 603,
        }
    )
    upsert_profile(
        {
            "user_id": 602,
            "category": "staff",
            "designation": "Head of Finance",
            "unit": "Finance",
            "unit_head_user_id": None,
            "sanction_authority_user_id": None,
        }
    )
    upsert_profile(
        {
            "user_id": 603,
            "category": "staff",
            "designation": "Registrar",
            "unit": "Admin",
            "unit_head_user_id": None,
            "sanction_authority_user_id": None,
        }
    )
    future_start = date.today() + timedelta(days=20)
    while future_start.weekday() >= 4:
        future_start += timedelta(days=1)
    future_end = future_start + timedelta(days=1)
    allot_balance(
        {
            "employee_id": 601,
            "category": "CL",
            "year": future_start.year,
            "allotted": Decimal("8.0"),
        }
    )

    app = submit(
        _principal(601),
        {
            "category": "CL",
            "start_date": future_start,
            "end_date": future_end,
            "reason": "Personal work",
        },
    )
    assert app.status == "PENDING"

    # Cannot cancel non-approved leave
    with pytest.raises(ValidationError, match=r"Only approved leave can be cancelled"):
        request_cancellation(_principal(601), app.id)

    decide(_principal(602), app.id, action="approve", remarks="Approved by Unit Head")
    app.refresh_from_db()
    assert app.status == "APPROVED"
    bal = LeaveBalance.objects.get(employee_id=601, year=future_start.year, category="CL")
    assert bal.used == Decimal("2.0")

    # Non-applicant cannot request cancellation
    with pytest.raises(Http404):
        request_cancellation(_principal(603), app.id)

    # Cancel pre-start request
    cancel_req = request_cancellation(_principal(601), app.id, remarks="Trip cancelled")
    assert cancel_req.status == "AWAITING_CANCEL"

    # Balance is NOT refunded on cancellation request
    bal.refresh_from_db()
    assert bal.used == Decimal("2.0")

    # Repeated cancellation request fails (already in AWAITING_CANCEL)
    with pytest.raises(ValidationError, match=r"Only approved leave can be cancelled"):
        request_cancellation(_principal(601), app.id)

    # Unauthorized approver cannot decide cancellation
    with pytest.raises(PermissionDenied, match=r"Only the assigned Unit Head can act now"):
        decide(_principal(603), app.id, action="approve_cancellation")

    # Unit Head rejects cancellation -> status restored to APPROVED, balance remains deducted
    rejected_cancel = decide(
        _principal(602), app.id, action="reject_cancellation", remarks="Workload is critical"
    )
    assert rejected_cancel.status == "APPROVED"
    bal.refresh_from_db()
    assert bal.used == Decimal("2.0")

    # Request cancellation again and approve -> balance refunded and status CANCELLED
    request_cancellation(_principal(601), app.id, remarks="Re-submitting cancellation")
    approved_cancel = decide(
        _principal(602), app.id, action="approve_cancellation", remarks="Approved cancellation"
    )
    assert approved_cancel.status == "CANCELLED"
    bal.refresh_from_db()
    assert bal.used == Decimal("0.0")


@pytest.mark.django_db
def test_higher_sanction_and_director_cancellation_workflows():
    # Setup for Higher Sanction (EL)
    upsert_profile(
        {
            "user_id": 610,
            "category": "faculty",
            "designation": "Assistant Professor",
            "unit": "CSE",
            "unit_head_user_id": 611,
            "sanction_authority_user_id": 612,
        }
    )
    upsert_profile(
        {
            "user_id": 611,
            "category": "faculty",
            "designation": "HOD CSE",
            "unit": "CSE",
            "unit_head_user_id": None,
            "sanction_authority_user_id": None,
        }
    )
    upsert_profile(
        {
            "user_id": 612,
            "category": "faculty",
            "designation": "Dean Faculty Affairs",
            "unit": "Administration",
            "unit_head_user_id": None,
            "sanction_authority_user_id": None,
        }
    )
    future_start = date.today() + timedelta(days=25)
    future_end = future_start + timedelta(days=2)
    allot_balance(
        {
            "employee_id": 610,
            "category": "EL",
            "year": future_start.year,
            "allotted": Decimal("30.0"),
        }
    )

    el_app = submit(
        _principal(610),
        {
            "category": "EL",
            "start_date": future_start,
            "end_date": future_end,
            "reason": "Conference",
        },
    )
    decide(_principal(611), el_app.id, action="recommend")
    decide(_principal(612), el_app.id, action="approve")
    el_app.refresh_from_db()
    assert el_app.status == "APPROVED"
    bal_el = LeaveBalance.objects.get(employee_id=610, year=future_start.year, category="EL")
    assert bal_el.used == Decimal("3.0")

    # Employee requests cancellation
    request_cancellation(_principal(610), el_app.id, remarks="Conference deferred")
    el_app.refresh_from_db()
    assert el_app.status == "AWAITING_CANCEL"
    bal_el.refresh_from_db()
    assert bal_el.used == Decimal("3.0")

    # Sanction Authority cannot decide before Unit Head recommendation
    with pytest.raises(PermissionDenied, match=r"Only the assigned Unit Head can act now"):
        decide(_principal(612), el_app.id, action="approve_cancellation")

    # Unit Head recommends cancellation
    decide(_principal(611), el_app.id, action="recommend", remarks="Recommended cancellation")
    el_app.refresh_from_db()
    assert el_app.status == "AWAITING_CANCEL"
    assert el_app.recommendation == "RECOMMENDED"

    # Unit Head cannot give final approval
    with pytest.raises(
        PermissionDenied, match=r"Only the assigned sanction authority can act now"
    ):
        decide(_principal(611), el_app.id, action="approve_cancellation")

    # Sanction Authority approves cancellation
    decide(_principal(612), el_app.id, action="approve_cancellation", remarks="Sanctioned cancel")
    el_app.refresh_from_db()
    assert el_app.status == "CANCELLED"
    bal_el.refresh_from_db()
    assert bal_el.used == Decimal("0.0")

    # Setup Director cancellation
    upsert_profile(
        {
            "user_id": 620,
            "category": "faculty",
            "designation": "Director",
            "unit": "Admin",
            "unit_head_user_id": None,
            "sanction_authority_user_id": None,
        }
    )
    allot_balance(
        {
            "employee_id": 620,
            "category": "EL",
            "year": future_start.year,
            "allotted": Decimal("30.0"),
        }
    )
    dir_app = submit(
        _principal(620),
        {
            "category": "EL",
            "start_date": future_start,
            "end_date": future_end,
            "reason": "Official summit",
        },
    )
    decide(_principal(620), dir_app.id, action="approve")
    bal_dir = LeaveBalance.objects.get(employee_id=620, year=future_start.year, category="EL")
    assert bal_dir.used == Decimal("3.0")

    # Director requests cancellation and self-sanctions
    request_cancellation(_principal(620), dir_app.id, remarks="Summit rescheduled")
    dir_app.refresh_from_db()
    assert dir_app.status == "AWAITING_CANCEL"

    with pytest.raises(
        PermissionDenied, match=r"Only the Director can self-sanction this leave"
    ):
        decide(_principal(611), dir_app.id, action="approve_cancellation")

    decide(_principal(620), dir_app.id, action="approve_cancellation", remarks="Self-cancelled")
    dir_app.refresh_from_db()
    assert dir_app.status == "CANCELLED"
    bal_dir.refresh_from_db()
    assert bal_dir.used == Decimal("0.0")


@pytest.mark.django_db
def test_substitute_permissions_and_approval_queue_access():
    emp_perms = {
        "leave_elm.application.view",
        "leave_elm.application.apply",
        "leave_elm.balance.view",
    }
    upsert_profile(
        {
            "user_id": 701,
            "category": "staff",
            "designation": "Clerk",
            "unit": "Store",
            "unit_head_user_id": 703,
            "sanction_authority_user_id": 704,
        }
    )
    upsert_profile(
        {
            "user_id": 702,
            "category": "staff",
            "designation": "Assistant",
            "unit": "Store",
            "unit_head_user_id": 703,
            "sanction_authority_user_id": 704,
        }
    )
    upsert_profile(
        {
            "user_id": 703,
            "category": "staff",
            "designation": "Store Officer",
            "unit": "Store",
            "unit_head_user_id": None,
            "sanction_authority_user_id": None,
        }
    )
    future_start = date.today() + timedelta(days=15)
    future_end = future_start + timedelta(days=1)
    allot_balance(
        {
            "employee_id": 702,
            "category": "CL",
            "year": future_start.year,
            "allotted": Decimal("8.0"),
        }
    )

    app = submit(
        _principal(702, permissions=emp_perms),
        {
            "category": "CL",
            "start_date": future_start,
            "end_date": future_end,
            "reason": "Personal emergency",
            "substitute_user_id": 701,
        },
    )
    assert app.status == "AWAITING_SUB"

    # Queue access: substitute 701 sees the task in approval queue
    sub_queue = list_approval_queue(701)
    assert any(item.id == app.id for item in sub_queue)

    other_queue = list_approval_queue(704)
    assert not any(item.id == app.id for item in other_queue)

    # Non-substitute employee cannot respond to substitute task
    with pytest.raises(
        PermissionDenied, match=r"Only the nominated substitute can respond now"
    ):
        decide(_principal(704, permissions=emp_perms), app.id, action="accept_substitute")

    # Regular employee without approval grant cannot perform approval action
    with pytest.raises(PermissionDenied, match=r"You do not have approval privileges"):
        decide(_principal(701, permissions=emp_perms), app.id, action="approve")

    # Nominated substitute accepts without approver role
    accepted = decide(
        _principal(701, permissions=emp_perms), app.id, action="accept_substitute"
    )
    assert accepted.status == "PENDING"
    assert accepted.substitute_status == "ACCEPTED"

    # Now task moved to Unit Head 703
    assert not any(item.id == app.id for item in list_approval_queue(701))
    assert any(item.id == app.id for item in list_approval_queue(703))


@pytest.mark.django_db
def test_substitute_decline_and_replacement_recovery_workflow():
    emp_perms = {
        "leave_elm.application.view",
        "leave_elm.application.apply",
        "leave_elm.balance.view",
    }
    upsert_profile(
        {
            "user_id": 801,
            "category": "staff",
            "designation": "Assistant",
            "unit": "Library",
            "unit_head_user_id": 804,
            "sanction_authority_user_id": 805,
        }
    )
    upsert_profile(
        {
            "user_id": 802,
            "category": "staff",
            "designation": "Assistant",
            "unit": "Library",
            "unit_head_user_id": 804,
            "sanction_authority_user_id": 805,
        }
    )
    upsert_profile(
        {
            "user_id": 803,
            "category": "staff",
            "designation": "Library Assistant",
            "unit": "Library",
            "unit_head_user_id": 804,
            "sanction_authority_user_id": 805,
        }
    )
    upsert_profile(
        {
            "user_id": 804,
            "category": "staff",
            "designation": "Librarian",
            "unit": "Library",
            "unit_head_user_id": None,
            "sanction_authority_user_id": None,
        }
    )
    future_start = date.today() + timedelta(days=10)
    while future_start.weekday() >= 4:
        future_start += timedelta(days=1)
    future_end = future_start + timedelta(days=1)
    allot_balance(
        {
            "employee_id": 801,
            "category": "CL",
            "year": future_start.year,
            "allotted": Decimal("8.0"),
        }
    )
    allot_balance(
        {
            "employee_id": 803,
            "category": "CL",
            "year": future_start.year,
            "allotted": Decimal("8.0"),
        }
    )

    app = submit(
        _principal(801, permissions=emp_perms),
        {
            "category": "CL",
            "start_date": future_start,
            "end_date": future_end,
            "reason": "Personal",
            "substitute_user_id": 802,
        },
    )
    assert app.status == "AWAITING_SUB"

    # Substitute declines -> enters ACTION_REQUIRED
    declined = decide(
        _principal(802, permissions=emp_perms),
        app.id,
        action="decline_substitute",
        remarks="Unavailable on these dates",
    )
    assert declined.status == "ACTION_REQUIRED"
    assert declined.substitute_status == "DECLINED"

    # Withdrawal from ACTION_REQUIRED is allowed
    withdrawn = withdraw(_principal(801, permissions=emp_perms), app.id)
    assert withdrawn.status == "WITHDRAWN"

    # New application to test replacement recovery
    second_start = future_start + timedelta(days=7)
    second_end = second_start + timedelta(days=1)
    app2 = submit(
        _principal(801, permissions=emp_perms),
        {
            "category": "CL",
            "start_date": second_start,
            "end_date": second_end,
            "reason": "Personal rescheduled",
            "substitute_user_id": 802,
        },
    )
    decide(
        _principal(802, permissions=emp_perms),
        app2.id,
        action="decline_substitute",
        remarks="Cannot take responsibility",
    )
    app2.refresh_from_db()
    assert app2.status == "ACTION_REQUIRED"

    # Replacement by non-applicant rejected
    with pytest.raises(Http404):
        replace_substitute(
            _principal(802, permissions=emp_perms), app2.id, new_substitute_user_id=803
        )

    # Replacement nominating self rejected
    with pytest.raises(ValidationError, match=r"Applicant cannot be their own substitute"):
        replace_substitute(
            _principal(801, permissions=emp_perms), app2.id, new_substitute_user_id=801
        )

    # Replacement nominating non-existent employee rejected
    with pytest.raises(ValidationError, match=r"must be an active employee"):
        replace_substitute(
            _principal(801, permissions=emp_perms), app2.id, new_substitute_user_id=9999
        )

    # Valid replacement succeeds -> returns to AWAITING_SUB
    replaced = replace_substitute(
        _principal(801, permissions=emp_perms), app2.id, new_substitute_user_id=803
    )
    assert replaced.status == "AWAITING_SUB"
    assert replaced.substitute_status == "PENDING"
    assert replaced.substitute_user_id == 803

    # New substitute accepts -> transitions to PENDING
    decide(_principal(803, permissions=emp_perms), app2.id, action="accept_substitute")
    app2.refresh_from_db()
    assert app2.status == "PENDING"
    assert app2.substitute_status == "ACCEPTED"

    # Unit head approves
    decide(_principal(804), app2.id, action="approve")
    app2.refresh_from_db()
    assert app2.status == "APPROVED"


@pytest.mark.django_db
def test_api_views_workflow_and_authorization():
    from rest_framework.test import APIRequestFactory

    from modules.elm.api.views import (
        ApprovalQueueView,
        CancelView,
        DecisionView,
        ReplaceSubstituteView,
    )

    factory = APIRequestFactory()
    emp_perms = {
        "leave_elm.application.view",
        "leave_elm.application.apply",
        "leave_elm.balance.view",
    }
    approver_perms = {
        "leave_elm.application.view",
        "leave_elm.application.approve",
        "leave_elm.balance.view",
    }

    upsert_profile(
        {
            "user_id": 901,
            "category": "staff",
            "designation": "Assistant",
            "unit": "Admin",
            "unit_head_user_id": 904,
            "sanction_authority_user_id": 904,
        }
    )
    upsert_profile(
        {
            "user_id": 902,
            "category": "staff",
            "designation": "Assistant",
            "unit": "Admin",
            "unit_head_user_id": 904,
            "sanction_authority_user_id": 904,
        }
    )
    upsert_profile(
        {
            "user_id": 903,
            "category": "staff",
            "designation": "Assistant",
            "unit": "Admin",
            "unit_head_user_id": 904,
            "sanction_authority_user_id": 904,
        }
    )
    upsert_profile(
        {
            "user_id": 904,
            "category": "staff",
            "designation": "Officer",
            "unit": "Admin",
            "unit_head_user_id": None,
            "sanction_authority_user_id": None,
        }
    )

    future_start = date.today() + timedelta(days=35)
    while future_start.weekday() >= 4:
        future_start += timedelta(days=1)
    future_end = future_start + timedelta(days=1)

    allot_balance(
        {
            "employee_id": 901,
            "category": "CL",
            "year": future_start.year,
            "allotted": Decimal("8.0"),
        }
    )

    # 1. Submit application with substitute 902
    app = submit(
        _principal(901, permissions=emp_perms),
        {
            "category": "CL",
            "start_date": future_start,
            "end_date": future_end,
            "reason": "Family function",
            "substitute_user_id": 902,
        },
    )
    assert app.status == "AWAITING_SUB"

    # 2. Test ApprovalQueueView for substitute (no HTTP 403)
    req = factory.get("/elm/approvals")
    req.principal = _principal(902, permissions=emp_perms)
    res = ApprovalQueueView.as_view()(req)
    assert res.status_code == 200
    assert any(item["id"] == app.id for item in res.data["results"])

    # 3. Test DecisionView: Substitute decline -> ACTION_REQUIRED
    req = factory.post(
        f"/elm/applications/{app.id}/decide",
        {"action": "decline_substitute", "remarks": "Out of town"},
        format="json",
    )
    req.principal = _principal(902, permissions=emp_perms)
    res = DecisionView.as_view()(req, pk=app.id)
    assert res.status_code == 200
    assert res.data["status"] == "ACTION_REQUIRED"
    assert res.data["substitute_status"] == "DECLINED"

    # 4. Test ReplaceSubstituteView: Applicant replaces substitute
    req = factory.post(
        f"/elm/applications/{app.id}/substitute",
        {"substitute_user_id": 903},
        format="json",
    )
    req.principal = _principal(901, permissions=emp_perms)
    res = ReplaceSubstituteView.as_view()(req, pk=app.id)
    assert res.status_code == 200
    assert res.data["status"] == "AWAITING_SUB"
    assert res.data["substitute_user_id"] == 903
    assert res.data["substitute_status"] == "PENDING"

    # 5. Substitute 2 accepts
    req = factory.post(
        f"/elm/applications/{app.id}/decide",
        {"action": "accept_substitute"},
        format="json",
    )
    req.principal = _principal(903, permissions=emp_perms)
    res = DecisionView.as_view()(req, pk=app.id)
    assert res.status_code == 200
    assert res.data["status"] == "PENDING"

    # 6. Ordinary employee (903) cannot approve leave
    req = factory.post(
        f"/elm/applications/{app.id}/decide",
        {"action": "approve"},
        format="json",
    )
    req.principal = _principal(903, permissions=emp_perms)
    res = DecisionView.as_view()(req, pk=app.id)
    assert res.status_code == 403

    # 7. Unit Head approves leave
    req = factory.post(
        f"/elm/applications/{app.id}/decide",
        {"action": "approve", "remarks": "Approved"},
        format="json",
    )
    req.principal = _principal(904, permissions=approver_perms)
    res = DecisionView.as_view()(req, pk=app.id)
    assert res.status_code == 200
    assert res.data["status"] == "APPROVED"

    # 8. Test CancelView: Applicant requests cancellation
    req = factory.post(
        f"/elm/applications/{app.id}/cancel",
        {"remarks": "Plan cancelled"},
        format="json",
    )
    req.principal = _principal(901, permissions=emp_perms)
    res = CancelView.as_view()(req, pk=app.id)
    assert res.status_code == 200
    assert res.data["status"] == "AWAITING_CANCEL"

    # Balance NOT refunded yet
    bal = LeaveBalance.objects.get(employee_id=901, year=future_start.year, category="CL")
    assert bal.used == Decimal("2.0")

    # 9. Unit Head approves cancellation
    req = factory.post(
        f"/elm/applications/{app.id}/decide",
        {"action": "approve_cancellation", "remarks": "Cancelled"},
        format="json",
    )
    req.principal = _principal(904, permissions=approver_perms)
    res = DecisionView.as_view()(req, pk=app.id)
    assert res.status_code == 200
    assert res.data["status"] == "CANCELLED"

    # Balance refunded now
    bal.refresh_from_db()
    assert bal.used == Decimal("0.0")


@pytest.mark.django_db
def test_higher_sanction_cancellation_order_and_out_of_order_rejection():
    """BR-EL-023 & CW-EL-02: Higher-sanction cancellation requires Unit Head recommendation first."""
    upsert_profile(
        {
            "user_id": 1101,
            "category": "staff",
            "designation": "Technical Officer",
            "unit": "Computer Center",
            "unit_head_user_id": 1102,
            "sanction_authority_user_id": 1103,
        }
    )
    today = timezone.localdate()
    future_start = today + timedelta(days=10)
    while future_start.weekday() >= 4:
        future_start += timedelta(days=1)
    future_end = future_start + timedelta(days=1)

    allot_balance(
        {"employee_id": 1101, "category": "EL", "year": future_start.year, "allotted": Decimal("15.0")}
    )
    app = submit(
        _principal(1101),
        {
            "category": "EL",
            "start_date": future_start,
            "end_date": future_end,
            "reason": "Personal work",
        },
    )
    # Unit Head recommends initial application
    decide(_principal(1102), app.id, action="recommend", remarks="Recommended")
    # Sanction Authority approves
    decide(_principal(1103), app.id, action="approve", remarks="Approved")
    app.refresh_from_db()
    assert app.status == "APPROVED"
    bal = LeaveBalance.objects.get(employee_id=1101, year=future_start.year, category="EL")
    assert bal.used == Decimal("2.0")

    # Applicant requests cancellation
    c_app = request_cancellation(_principal(1101), app.id, remarks="Plans changed")
    assert c_app.status == "AWAITING_CANCEL"
    assert c_app.recommendation == ""

    # Queue inspection: Unit Head sees it, Sanction Authority does not see it yet
    uh_queue = [x.id for x in list_approval_queue(1102)]
    sa_queue = [x.id for x in list_approval_queue(1103)]
    assert app.id in uh_queue
    assert app.id not in sa_queue

    # Out-of-order rejection: Sanction Authority cannot act before Unit Head recommends
    with pytest.raises(PermissionDenied, match=r"Only the assigned Unit Head can act now\."):
        decide(_principal(1103), app.id, action="approve_cancellation")

    # Invalid action: Unit Head cannot approve cancellation directly for higher-sanction leave
    with pytest.raises(ValidationError) as exc:
        decide(_principal(1102), app.id, action="approve_cancellation")
    assert "Unit Head must recommend or not recommend cancellation." in str(exc.value)

    # Unit Head recommends cancellation
    rec_c = decide(_principal(1102), app.id, action="recommend", remarks="Cancellation recommended")
    assert rec_c.status == "AWAITING_CANCEL"
    assert rec_c.recommendation == "RECOMMENDED"

    # Balance is NOT yet refunded
    bal.refresh_from_db()
    assert bal.used == Decimal("2.0")

    # Queue inspection: Unit Head no longer sees it, Sanction Authority sees it now
    uh_queue2 = [x.id for x in list_approval_queue(1102)]
    sa_queue2 = [x.id for x in list_approval_queue(1103)]
    assert app.id not in uh_queue2
    assert app.id in sa_queue2

    # Out-of-order rejection: Unit Head cannot act again after recommending
    with pytest.raises(PermissionDenied, match=r"Only the assigned sanction authority can act now\."):
        decide(_principal(1102), app.id, action="recommend")

    # Sanction Authority approves cancellation
    fin_c = decide(_principal(1103), app.id, action="approve_cancellation", remarks="Approved cancellation")
    assert fin_c.status == "CANCELLED"

    # Balance is refunded exactly once
    bal.refresh_from_db()
    assert bal.used == Decimal("0.0")


@pytest.mark.django_db
def test_cancellation_rejected_on_exact_leave_start_date():
    """Cancellation requested on today == start_date is rejected with ValidationError."""
    today = timezone.localdate()
    upsert_profile(
        {
            "user_id": 1201,
            "category": "staff",
            "designation": "Assistant",
            "unit": "Accounts",
            "unit_head_user_id": 1202,
        }
    )
    allot_balance(
        {"employee_id": 1201, "category": "CL", "year": today.year, "allotted": Decimal("8.0")}
    )
    app = submit(
        _principal(1201),
        {
            "category": "CL",
            "start_date": today,
            "end_date": today,
            "reason": "Sick",
        },
    )
    decide(_principal(1202), app.id, action="approve")
    app.refresh_from_db()
    assert app.status == "APPROVED"

    with pytest.raises(ValidationError) as exc:
        request_cancellation(_principal(1201), app.id)
    assert "Approved leave cannot be cancelled once started." in str(exc.value)


@pytest.mark.django_db
def test_duplicate_cancellation_decision_rejected_without_double_refund():
    """Repeated cancellation decisions on already finalized leaves are rejected without double-refund."""
    today = timezone.localdate()
    future_start = today + timedelta(days=10)
    while future_start.weekday() >= 4:
        future_start += timedelta(days=1)

    upsert_profile(
        {
            "user_id": 1211,
            "category": "staff",
            "designation": "Assistant",
            "unit": "Accounts",
            "unit_head_user_id": 1212,
        }
    )
    allot_balance(
        {"employee_id": 1211, "category": "CL", "year": future_start.year, "allotted": Decimal("8.0")}
    )
    app = submit(
        _principal(1211),
        {
            "category": "CL",
            "start_date": future_start,
            "end_date": future_start,
            "reason": "Personal",
        },
    )
    decide(_principal(1212), app.id, action="approve")
    request_cancellation(_principal(1211), app.id)
    decide(_principal(1212), app.id, action="approve_cancellation")

    bal = LeaveBalance.objects.get(employee_id=1211, year=future_start.year, category="CL")
    assert bal.used == Decimal("0.0")

    # Second decision attempt
    with pytest.raises(ValidationError) as exc:
        decide(_principal(1212), app.id, action="approve_cancellation")
    assert "This application is no longer actionable." in str(exc.value)

    bal.refresh_from_db()
    assert bal.used == Decimal("0.0")


@pytest.mark.django_db
def test_cancellation_refund_inconsistent_balance_integrity_rollback():
    """If balance.used < application.duration, raise ValidationError and rollback without state change."""
    today = timezone.localdate()
    future_start = today + timedelta(days=10)
    while future_start.weekday() >= 4:
        future_start += timedelta(days=1)
    future_end = future_start + timedelta(days=1)

    upsert_profile(
        {
            "user_id": 1221,
            "category": "staff",
            "designation": "Assistant",
            "unit": "Admin",
            "unit_head_user_id": 1222,
        }
    )
    allot_balance(
        {"employee_id": 1221, "category": "CL", "year": future_start.year, "allotted": Decimal("10.0")}
    )
    app = submit(
        _principal(1221),
        {
            "category": "CL",
            "start_date": future_start,
            "end_date": future_end,
            "reason": "Trip",
        },
    )
    decide(_principal(1222), app.id, action="approve")
    request_cancellation(_principal(1221), app.id)

    # Inconsistent balance condition (e.g. balance manually changed to 1.0 while leave duration is 2.0)
    bal = LeaveBalance.objects.get(employee_id=1221, year=future_start.year, category="CL")
    bal.used = Decimal("1.0")
    bal.save(update_fields=["used"])

    with pytest.raises(ValidationError) as exc:
        decide(_principal(1222), app.id, action="approve_cancellation")
    assert "Cannot refund more leave days than currently recorded as used." in str(exc.value)

    # Verify rollback
    app.refresh_from_db()
    assert app.status == "AWAITING_CANCEL"
    bal.refresh_from_db()
    assert bal.used == Decimal("1.0")


@pytest.mark.django_db
def test_old_substitute_cannot_respond_after_replacement():
    """EL-UC-019: Previous substitute attempting to respond after replacement receives PermissionDenied."""
    today = timezone.localdate()
    future_start = today + timedelta(days=10)
    while future_start.weekday() >= 4:
        future_start += timedelta(days=1)

    for uid in (1301, 1302, 1303, 1304):
        upsert_profile(
            {
                "user_id": uid,
                "category": "staff",
                "designation": "Assistant",
                "unit": "Operations",
                "unit_head_user_id": 1304,
            }
        )
    allot_balance(
        {"employee_id": 1301, "category": "CL", "year": future_start.year, "allotted": Decimal("8.0")}
    )

    app = submit(
        _principal(1301),
        {
            "category": "CL",
            "start_date": future_start,
            "end_date": future_start,
            "reason": "Duty",
            "substitute_user_id": 1302,
        },
    )
    assert app.status == "AWAITING_SUB"

    # Sub1 declines
    decide(_principal(1302), app.id, action="decline_substitute")
    app.refresh_from_db()
    assert app.status == "ACTION_REQUIRED"

    # Applicant replaces with Sub2
    replace_substitute(_principal(1301), app.id, new_substitute_user_id=1303)
    app.refresh_from_db()
    assert app.status == "AWAITING_SUB"
    assert app.substitute_user_id == 1303

    # Old substitute (1302) attempts to respond
    with pytest.raises(PermissionDenied, match=r"Only the nominated substitute can respond now\."):
        decide(_principal(1302), app.id, action="accept_substitute")

    with pytest.raises(PermissionDenied, match=r"Only the nominated substitute can respond now\."):
        decide(_principal(1302), app.id, action="decline_substitute")

    # New substitute (1303) accepts successfully
    decide(_principal(1303), app.id, action="accept_substitute")
    app.refresh_from_db()
    assert app.status == "PENDING"
    assert app.substitute_status == "ACCEPTED"


@pytest.mark.django_db
def test_unauthorized_user_cannot_replace_substitute():
    """Only applicant can nominate replacement substitute; others receive Http404."""
    today = timezone.localdate()
    future_start = today + timedelta(days=10)
    while future_start.weekday() >= 4:
        future_start += timedelta(days=1)

    for uid in (1401, 1402, 1403, 1404):
        upsert_profile(
            {
                "user_id": uid,
                "category": "staff",
                "designation": "Assistant",
                "unit": "Logistics",
                "unit_head_user_id": 1404,
            }
        )
    allot_balance(
        {"employee_id": 1401, "category": "CL", "year": future_start.year, "allotted": Decimal("8.0")}
    )

    app = submit(
        _principal(1401),
        {
            "category": "CL",
            "start_date": future_start,
            "end_date": future_start,
            "reason": "Personal",
            "substitute_user_id": 1402,
        },
    )
    decide(_principal(1402), app.id, action="decline_substitute")

    # Non-applicant attempts replace_substitute
    with pytest.raises(Http404):
        replace_substitute(_principal(1403), app.id, new_substitute_user_id=1402)


@pytest.mark.django_db
def test_substitute_overlap_with_awaiting_cancel_leave_rejected():
    """BR-EL-014: Substitute with leave in AWAITING_CANCEL cannot be nominated as substitute."""
    today = timezone.localdate()
    future_start = today + timedelta(days=10)
    while future_start.weekday() >= 4:
        future_start += timedelta(days=1)

    for uid in (1501, 1502, 1503):
        upsert_profile(
            {
                "user_id": uid,
                "category": "staff",
                "designation": "Assistant",
                "unit": "Facilities",
                "unit_head_user_id": 1503,
            }
        )
    allot_balance(
        {"employee_id": 1501, "category": "CL", "year": future_start.year, "allotted": Decimal("8.0")}
    )
    allot_balance(
        {"employee_id": 1502, "category": "CL", "year": future_start.year, "allotted": Decimal("8.0")}
    )

    # 1502 has approved leave that is now in AWAITING_CANCEL
    sub_leave = submit(
        _principal(1502),
        {
            "category": "CL",
            "start_date": future_start,
            "end_date": future_start,
            "reason": "Leave",
        },
    )
    decide(_principal(1503), sub_leave.id, action="approve")
    request_cancellation(_principal(1502), sub_leave.id)
    sub_leave.refresh_from_db()
    assert sub_leave.status == "AWAITING_CANCEL"

    # 1501 tries to nominate 1502 on submit
    with pytest.raises(ValidationError) as exc:
        submit(
            _principal(1501),
            {
                "category": "CL",
                "start_date": future_start,
                "end_date": future_start,
                "reason": "Personal",
                "substitute_user_id": 1502,
            },
        )
    assert "Nominated substitute has overlapping leave." in str(exc.value)


@pytest.mark.django_db
def test_applicant_overlap_with_awaiting_cancel_and_action_required_rejected():
    """Applicant cannot submit overlapping leave while another leave is AWAITING_CANCEL or ACTION_REQUIRED."""
    today = timezone.localdate()
    future_start = today + timedelta(days=10)
    while future_start.weekday() >= 4:
        future_start += timedelta(days=1)

    for uid in (1601, 1602, 1603):
        upsert_profile(
            {
                "user_id": uid,
                "category": "staff",
                "designation": "Assistant",
                "unit": "HR",
                "unit_head_user_id": 1603,
            }
        )
    allot_balance(
        {"employee_id": 1601, "category": "CL", "year": future_start.year, "allotted": Decimal("8.0")}
    )

    # 1. Overlap with own AWAITING_CANCEL
    app1 = submit(
        _principal(1601),
        {
            "category": "CL",
            "start_date": future_start,
            "end_date": future_start,
            "reason": "First leave",
        },
    )
    decide(_principal(1603), app1.id, action="approve")
    request_cancellation(_principal(1601), app1.id)

    with pytest.raises(ValidationError) as exc:
        submit(
            _principal(1601),
            {
                "category": "CL",
                "start_date": future_start,
                "end_date": future_start,
                "reason": "Second overlapping leave",
            },
        )
    assert "An active leave request overlaps these dates." in str(exc.value)

    # 2. Overlap with own ACTION_REQUIRED
    future_start2 = future_start + timedelta(days=7)
    while future_start2.weekday() >= 4:
        future_start2 += timedelta(days=1)

    app2 = submit(
        _principal(1601),
        {
            "category": "CL",
            "start_date": future_start2,
            "end_date": future_start2,
            "reason": "Leave with sub",
            "substitute_user_id": 1602,
        },
    )
    decide(_principal(1602), app2.id, action="decline_substitute")
    app2.refresh_from_db()
    assert app2.status == "ACTION_REQUIRED"

    with pytest.raises(ValidationError) as exc2:
        submit(
            _principal(1601),
            {
                "category": "CL",
                "start_date": future_start2,
                "end_date": future_start2,
                "reason": "Overlapping while sub declined",
            },
        )
    assert "An active leave request overlaps these dates." in str(exc2.value)


@pytest.mark.django_db
def test_leave_extension_workflow_and_incremental_posting():
    """CW-EL-03 & BR-EL-025: Extension requested on ongoing EL, incremental balance posted only on approval."""
    today = timezone.localdate()
    year = today.year
    upsert_profile(
        {
            "user_id": 1701,
            "category": "staff",
            "designation": "Executive Engineer",
            "unit": "Works",
            "unit_head_user_id": 1702,
            "sanction_authority_user_id": 1703,
        }
    )
    allot_balance(
        {"employee_id": 1701, "category": "EL", "year": year, "allotted": Decimal("30.0")}
    )

    base_start = today - timedelta(days=2)
    base_end = today + timedelta(days=2)
    ext_end = base_end + timedelta(days=4)

    # 1. Base leave: 5 days EL ongoing across today
    base_app = submit(
        _principal(1701),
        {
            "category": "EL",
            "start_date": base_start,
            "end_date": base_end,
            "reason": "Family trip",
        },
    )
    decide(_principal(1702), base_app.id, action="recommend")
    decide(_principal(1703), base_app.id, action="approve")
    base_app.refresh_from_db()
    assert base_app.status == "APPROVED"
    assert base_app.duration == Decimal("5.0")

    bal = LeaveBalance.objects.get(employee_id=1701, year=year, category="EL")
    assert bal.used == Decimal("5.0")

    # 2. Request extension for 4 additional days
    ext_app = request_extension(
        _principal(1701),
        pk=base_app.id,
        data={
            "extended_end_date": ext_end,
            "reason": "Extension needed due to travel delay",
        },
    )
    assert ext_app.original_application_id == base_app.id
    assert ext_app.category == "EL"
    assert ext_app.start_date == base_end + timedelta(days=1)
    assert ext_app.end_date == ext_end
    assert ext_app.duration == Decimal("4.0")
    assert ext_app.status == "PENDING"

    # Verify incremental duration is NOT yet posted to balance (remains 5.0)
    bal.refresh_from_db()
    assert bal.used == Decimal("5.0")

    # 3. Approve extension: Unit Head recommends, Sanction Authority approves
    decide(_principal(1702), ext_app.id, action="recommend")
    decide(_principal(1703), ext_app.id, action="approve")

    ext_app.refresh_from_db()
    assert ext_app.status == "APPROVED"

    # Incremental days now posted
    bal.refresh_from_db()
    assert bal.used == Decimal("9.0")  # 5.0 original + 4.0 extension

    # Base leave remains intact and APPROVED
    base_app.refresh_from_db()
    assert base_app.status == "APPROVED"
    assert base_app.end_date == base_end


@pytest.mark.django_db
def test_leave_extension_rejection_and_withdrawal_preserves_base():
    """CW-EL-03: Rejection or withdrawal of extension leaves base application intact."""
    today = timezone.localdate()
    year = today.year
    upsert_profile(
        {
            "user_id": 1711,
            "category": "staff",
            "designation": "Assistant",
            "unit": "Accounts",
            "unit_head_user_id": 1712,
            "sanction_authority_user_id": 1713,
        }
    )
    allot_balance(
        {"employee_id": 1711, "category": "EL", "year": year, "allotted": Decimal("30.0")}
    )

    base_start = today - timedelta(days=1)
    base_end = today + timedelta(days=3)
    ext_end1 = base_end + timedelta(days=3)
    ext_end2 = base_end + timedelta(days=2)

    base_app = submit(
        _principal(1711),
        {
            "category": "EL",
            "start_date": base_start,
            "end_date": base_end,
            "reason": "Personal",
        },
    )
    decide(_principal(1712), base_app.id, action="recommend")
    decide(_principal(1713), base_app.id, action="approve")

    bal = LeaveBalance.objects.get(employee_id=1711, year=year, category="EL")
    assert bal.used == Decimal("5.0")

    # Rejection scenario
    ext1 = request_extension(
        _principal(1711),
        pk=base_app.id,
        data={
            "extended_end_date": ext_end1,
            "reason": "Medical extension",
        },
    )
    decide(_principal(1712), ext1.id, action="recommend")
    decide(_principal(1713), ext1.id, action="reject", remarks="Cannot spare staff")
    ext1.refresh_from_db()
    assert ext1.status == "REJECTED"

    base_app.refresh_from_db()
    assert base_app.status == "APPROVED"
    bal.refresh_from_db()
    assert bal.used == Decimal("5.0")

    # Withdrawal scenario
    ext2 = request_extension(
        _principal(1711),
        pk=base_app.id,
        data={
            "extended_end_date": ext_end2,
            "reason": "Another request",
        },
    )
    withdraw(_principal(1711), ext2.id)
    ext2.refresh_from_db()
    assert ext2.status == "WITHDRAWN"

    base_app.refresh_from_db()
    assert base_app.status == "APPROVED"
    bal.refresh_from_db()
    assert bal.used == Decimal("5.0")


@pytest.mark.django_db
def test_leave_extension_validation_guards():
    """CW-EL-03 guards: category eligibility, date bounds, concurrent extension limits."""
    today = timezone.localdate()
    year = today.year
    upsert_profile(
        {
            "user_id": 1721,
            "category": "staff",
            "designation": "Assistant",
            "unit": "Accounts",
            "unit_head_user_id": 1722,
            "sanction_authority_user_id": 1723,
        }
    )
    allot_balance(
        {"employee_id": 1721, "category": "CL", "year": year, "allotted": Decimal("8.0")}
    )
    allot_balance(
        {"employee_id": 1721, "category": "EL", "year": year, "allotted": Decimal("30.0")}
    )

    cl_start = today - timedelta(days=6)
    cl_end = today - timedelta(days=5)
    base_start = today - timedelta(days=1)
    base_end = today + timedelta(days=2)
    ext_end = base_end + timedelta(days=3)

    # 1. Reject extension on CL
    cl_app = submit(
        _principal(1721),
        {
            "category": "CL",
            "start_date": cl_start,
            "end_date": cl_end,
            "reason": "CL Leave",
        },
    )
    decide(_principal(1722), cl_app.id, action="approve")

    with pytest.raises(ValidationError, match=r"Extension is only available for ongoing EL, COL, or VL\."):
        request_extension(
            _principal(1721),
            pk=cl_app.id,
            data={"extended_end_date": ext_end, "reason": "more time"},
        )

    # 2. Reject extension on unapproved EL
    el_app = submit(
        _principal(1721),
        {
            "category": "EL",
            "start_date": base_start,
            "end_date": base_end,
            "reason": "EL Leave",
        },
    )
    with pytest.raises(ValidationError, match=r"Only approved leave can be extended\."):
        request_extension(
            _principal(1721),
            pk=el_app.id,
            data={"extended_end_date": ext_end, "reason": "more time"},
        )

    # Approve el_app
    decide(_principal(1722), el_app.id, action="recommend")
    decide(_principal(1723), el_app.id, action="approve")

    # 3. Reject extension with date <= base end date
    with pytest.raises(ValidationError, match=r"Extended end date must be after original end date\."):
        request_extension(
            _principal(1721),
            pk=el_app.id,
            data={"extended_end_date": base_end, "reason": "more time"},
        )

    # 4. Reject unauthorized user requesting extension
    with pytest.raises(Http404):
        request_extension(
            _principal(1722),
            pk=el_app.id,
            data={"extended_end_date": ext_end, "reason": "more time"},
        )

    # 5. Prevent duplicate pending extensions
    request_extension(
        _principal(1721),
        pk=el_app.id,
        data={"extended_end_date": ext_end, "reason": "more time"},
    )
    with pytest.raises(ValidationError, match=r"An extension request is already pending for this leave\."):
        request_extension(
            _principal(1721),
            pk=el_app.id,
            data={"extended_end_date": ext_end + timedelta(days=2), "reason": "even more time"},
        )


@pytest.mark.django_db
def test_duty_resumption_workflow_normal_early_late():
    """CW-EL-04 & BR-EL-027, BR-EL-028: Normal, early (refund), and late (deduct) duty resumption."""
    upsert_profile(
        {
            "user_id": 1731,
            "category": "staff",
            "designation": "Section Officer",
            "unit": "Administration",
            "unit_head_user_id": 1732,
            "sanction_authority_user_id": 1733,
        }
    )
    allot_balance(
        {"employee_id": 1731, "category": "EL", "year": 2026, "allotted": Decimal("30.0")}
    )

    # 1. Normal return (resumed_at == end_date)
    app1 = submit(
        _principal(1731),
        {
            "category": "EL",
            "start_date": date(2026, 12, 1),
            "end_date": date(2026, 12, 5),
            "reason": "Dec Leave",
        },
    )
    decide(_principal(1732), app1.id, action="recommend")
    decide(_principal(1733), app1.id, action="approve")
    bal = LeaveBalance.objects.get(employee_id=1731, year=2026, category="EL")
    assert bal.used == Decimal("5.0")

    submit_resumption(_principal(1731), app1.id, resumption_date=date(2026, 12, 5))
    app1.refresh_from_db()
    assert app1.status == "AWAITING_RESUMPTION"

    # Queue check: sanction authority sees it
    queue = list_approval_queue(_principal(1733))
    assert any(q.id == app1.id for q in queue)

    # Unit Head cannot review resumption (only Sanction Authority)
    with pytest.raises(PermissionDenied, match=r"Only the assigned sanction authority can review resumption\."):
        review_resumption(_principal(1732), app1.id)

    # Sanction Authority reviews
    decide(_principal(1733), app1.id, action="review_resumption", remarks="Noted normal return")
    app1.refresh_from_db()
    assert app1.status == "COMPLETED"
    assert app1.resumed_at == date(2026, 12, 5)
    bal.refresh_from_db()
    assert bal.used == Decimal("5.0")

    # 2. Early return (resumed_at < end_date -> refund unused days)
    app2 = submit(
        _principal(1731),
        {
            "category": "EL",
            "start_date": date(2026, 12, 8),
            "end_date": date(2026, 12, 12),
            "reason": "Dec Leave 2",
        },
    )
    decide(_principal(1732), app2.id, action="recommend")
    decide(_principal(1733), app2.id, action="approve")
    bal.refresh_from_db()
    assert bal.used == Decimal("10.0")  # 5 + 5

    # Returned on Dec 10 instead of Dec 12 (returned 2 days early)
    submit_resumption(_principal(1731), app2.id, resumption_date=date(2026, 12, 10))
    app2.refresh_from_db()
    assert app2.status == "AWAITING_RESUMPTION"

    review_resumption(_principal(1733), app2.id, remarks="Approved early resumption")
    app2.refresh_from_db()
    assert app2.status == "COMPLETED"
    assert app2.end_date == date(2026, 12, 10)
    assert app2.duration == Decimal("3.0")
    bal.refresh_from_db()
    assert bal.used == Decimal("8.0")  # 10.0 - 2.0 refunded!

    # 3. Late return (resumed_at > end_date -> deduct extra days)
    app3 = submit(
        _principal(1731),
        {
            "category": "EL",
            "start_date": date(2026, 12, 15),
            "end_date": date(2026, 12, 18),
            "reason": "Dec Leave 3",
        },
    )
    decide(_principal(1732), app3.id, action="recommend")
    decide(_principal(1733), app3.id, action="approve")
    bal.refresh_from_db()
    assert bal.used == Decimal("12.0")  # 8 + 4

    # Returned on Dec 20 instead of Dec 18 (2 days late)
    submit_resumption(_principal(1731), app3.id, resumption_date=date(2026, 12, 20))
    app3.refresh_from_db()
    assert app3.status == "AWAITING_RESUMPTION"

    review_resumption(_principal(1733), app3.id, remarks="Approved late resumption adjustment")
    app3.refresh_from_db()
    assert app3.status == "COMPLETED"
    assert app3.end_date == date(2026, 12, 20)
    assert app3.duration == Decimal("6.0")
    bal.refresh_from_db()
    assert bal.used == Decimal("14.0")  # 12.0 + 2.0 deducted!


@pytest.mark.django_db
def test_year_end_balance_rollover():
    """EL-UC-020 & BR-EL-002-009: Annual balance rollover, VL->EL conversion, caps, and lapsing."""
    admin = _principal(1800, permissions={"leave_elm.admin.manage"})
    user = _principal(1801)

    # Non-admin rejected
    with pytest.raises(PermissionDenied, match=r"Only administrators can perform year-end rollover\."):
        rollover_balances(user, year=2026)

    # Set up faculty employee 1801:
    upsert_profile(
        {
            "user_id": 1801,
            "category": "faculty",
            "designation": "Associate Professor",
            "unit": "ECE",
            "unit_head_user_id": 1805,
        }
    )
    allot_balance({"employee_id": 1801, "category": "VL", "year": 2026, "allotted": Decimal("60.0")})
    allot_balance({"employee_id": 1801, "category": "EL", "year": 2026, "allotted": Decimal("10.0")})
    allot_balance({"employee_id": 1801, "category": "CL", "year": 2026, "allotted": Decimal("8.0")})
    allot_balance({"employee_id": 1801, "category": "RH", "year": 2026, "allotted": Decimal("2.0")})
    allot_balance({"employee_id": 1801, "category": "SCL", "year": 2026, "allotted": Decimal("15.0")})

    # Faculty used 25 VL, 3 CL, 1 RH
    b_vl = LeaveBalance.objects.get(employee_id=1801, year=2026, category="VL")
    b_vl.used = Decimal("25.0")  # Unused = 35.0 -> converts to 35/2 = 17.5 EL!
    b_vl.save()

    b_cl = LeaveBalance.objects.get(employee_id=1801, year=2026, category="CL")
    b_cl.used = Decimal("3.0")
    b_cl.save()

    # Set up staff employee 1802 (standard carry forward):
    upsert_profile(
        {
            "user_id": 1802,
            "category": "staff",
            "designation": "Accountant",
            "unit": "Accounts",
            "unit_head_user_id": 1805,
        }
    )
    allot_balance({"employee_id": 1802, "category": "EL", "year": 2026, "allotted": Decimal("30.0")})
    allot_balance({"employee_id": 1802, "category": "COL", "year": 2026, "allotted": Decimal("20.0")})
    b_el2 = LeaveBalance.objects.get(employee_id=1802, year=2026, category="EL")
    b_el2.used = Decimal("10.0")  # Unused = 20.0
    b_el2.save()
    b_col2 = LeaveBalance.objects.get(employee_id=1802, year=2026, category="COL")
    b_col2.used = Decimal("5.0")  # Unused = 15.0
    b_col2.save()

    # Set up staff employee 1803 (statutory cap 300 test):
    upsert_profile(
        {
            "user_id": 1803,
            "category": "staff",
            "designation": "Registrar",
            "unit": "Registry",
        }
    )
    allot_balance({"employee_id": 1803, "category": "EL", "year": 2026, "allotted": Decimal("290.0")})
    # Unused = 290.0. Adding 30 would make 320, but must be capped at 300!

    # Execute rollover
    res = rollover_balances(admin, year=2026)
    assert res["year"] == 2026
    assert res["next_year"] == 2027

    # Verify Faculty 1801 for 2027:
    # 1. Fresh 60 VL allotted, 0 used
    bal_vl_2027 = LeaveBalance.objects.get(employee_id=1801, year=2027, category="VL")
    assert bal_vl_2027.allotted == Decimal("60.0")
    assert bal_vl_2027.used == Decimal("0.0")

    # 2. EL: 10 existing + 17.5 converted from 35 unused VL = 27.5 EL
    bal_el_2027 = LeaveBalance.objects.get(employee_id=1801, year=2027, category="EL")
    assert bal_el_2027.allotted == Decimal("27.5")
    assert bal_el_2027.used == Decimal("0.0")

    # 3. CL fresh 8.0 (old 5 lapsed)
    bal_cl_2027 = LeaveBalance.objects.get(employee_id=1801, year=2027, category="CL")
    assert bal_cl_2027.allotted == Decimal("8.0")
    assert bal_cl_2027.used == Decimal("0.0")

    # 4. RH fresh 2.0
    bal_rh_2027 = LeaveBalance.objects.get(employee_id=1801, year=2027, category="RH")
    assert bal_rh_2027.allotted == Decimal("2.0")

    # 5. SCL fresh 15.0
    bal_scl_2027 = LeaveBalance.objects.get(employee_id=1801, year=2027, category="SCL")
    assert bal_scl_2027.allotted == Decimal("15.0")

    # Verify Staff 1802 for 2027:
    # EL: 20 unused + 30 new = 50.0
    bal_el_staff = LeaveBalance.objects.get(employee_id=1802, year=2027, category="EL")
    assert bal_el_staff.allotted == Decimal("50.0")

    # COL: 15 unused + 20 new = 35.0
    bal_col_staff = LeaveBalance.objects.get(employee_id=1802, year=2027, category="COL")
    assert bal_col_staff.allotted == Decimal("35.0")

    # Verify Staff 1803 cap for 2027:
    bal_el_capped = LeaveBalance.objects.get(employee_id=1803, year=2027, category="EL")
    assert bal_el_capped.allotted == Decimal("300.0")

    # Idempotency check: running rollover again for 2026 fails
    with pytest.raises(ValidationError, match=r"Year-end rollover for 2026 has already been processed\."):
        rollover_balances(admin, year=2026)


@pytest.mark.django_db
def test_offline_sanctioned_leave_recording():
    """BR-EL-029 & EL-UC-016: Admin records offline-approved leave with mandatory sanction reference."""
    admin = _principal(1900, permissions={"leave_elm.admin.manage"})
    user = _principal(1901)

    upsert_profile(
        {
            "user_id": 1902,
            "category": "staff",
            "designation": "Library Assistant",
            "unit": "Library",
        }
    )
    allot_balance({"employee_id": 1902, "category": "EL", "year": 2026, "allotted": Decimal("30.0")})

    # 1. Non-admin rejected
    with pytest.raises(PermissionDenied, match=r"Only administrators can record offline-sanctioned leave\."):
        record_offline_leave(
            user,
            {
                "employee_id": 1902,
                "category": "EL",
                "start_date": date(2026, 11, 23),
                "end_date": date(2026, 11, 27),
                "sanction_reference": "EST/2026/OFF-01",
            },
        )

    # 2. Missing sanction_reference rejected
    with pytest.raises(ValidationError, match=r"Sanction reference evidence is mandatory for offline leave\."):
        record_offline_leave(
            admin,
            {
                "employee_id": 1902,
                "category": "EL",
                "start_date": date(2026, 11, 23),
                "end_date": date(2026, 11, 27),
                "sanction_reference": "   ",
            },
        )

    # 3. Successful offline leave creation
    app = record_offline_leave(
        admin,
        {
            "employee_id": 1902,
            "category": "EL",
            "start_date": date(2026, 11, 23),
            "end_date": date(2026, 11, 27),
            "reason": "Paper approved leave",
            "sanction_reference": "EST/2026/OFF-01",
        },
    )
    assert app.status == "APPROVED"
    assert app.is_offline is True
    assert app.sanction_reference == "EST/2026/OFF-01"
    assert app.duration == Decimal("5.0")

    # Balance is immediately deducted without initiating approval workflow
    bal = LeaveBalance.objects.get(employee_id=1902, year=2026, category="EL")
    assert bal.used == Decimal("5.0")

    # 4. Duplicate sanction_reference rejected
    with pytest.raises(
        ValidationError,
        match=r"An offline leave with this sanction reference has already been recorded\.",
    ):
        record_offline_leave(
            admin,
            {
                "employee_id": 1902,
                "category": "EL",
                "start_date": date(2026, 12, 1),
                "end_date": date(2026, 12, 4),
                "sanction_reference": "EST/2026/OFF-01",
            },
        )



