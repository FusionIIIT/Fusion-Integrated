"""Integration tests for ELM services, selectors, and cross-module contracts."""

from datetime import date, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from modules.elm.contracts import get_employee_leave_profiles
from modules.elm.models import (
    LeaveAccountTransaction,
    LeaveBalance,
    LeaveNotification,
    SlaConfig,
)
from modules.elm.selectors.queries import (
    get_accessible_application,
    list_approval_queue,
)
from modules.elm.services.leave import (
    allot_balance,
    decide,
    execute_year_end_processing,
    nominate_replacement_substitute,
    process_sla_thresholds,
    record_offline_leave,
    request_cancellation,
    review_resumption,
    submit,
    submit_extension,
    submit_resumption,
    upsert_profile,
)


def _principal(user_id: int) -> SimpleNamespace:
    return SimpleNamespace(user_id=user_id)


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
    allot_balance({"employee_id": 101, "category": "CL", "year": 2026, "allotted": Decimal("8.0")})
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
    assert LeaveAccountTransaction.objects.filter(
        employee_id=101, transaction_type="DEBIT"
    ).exists()


@pytest.mark.django_db
def test_director_self_sanction_flow():
    upsert_profile(
        {
            "user_id": 1,
            "category": "faculty",
            "designation": "Director",
            "unit": "Directorate",
            "unit_head_user_id": None,
            "sanction_authority_user_id": None,
        }
    )
    allot_balance({"employee_id": 1, "category": "EL", "year": 2026, "allotted": Decimal("30.0")})

    app = submit(
        _principal(1),
        {
            "category": "EL",
            "start_date": date(2026, 11, 2),
            "end_date": date(2026, 11, 4),
            "reason": "Official Institute Visit",
        },
    )
    assert app.status == "AWAITING_DIRECTOR"
    assert app.duration == Decimal("3.0")

    queue = list(list_approval_queue(1))
    assert app in queue

    with pytest.raises(PermissionDenied):
        decide(_principal(999), app.id, action="approve")

    decided = decide(_principal(1), app.id, action="approve", remarks="Self-sanctioned as Director")
    assert decided.status == "APPROVED"
    bal = LeaveBalance.objects.get(employee_id=1, year=2026, category="EL")
    assert bal.used == Decimal("3.0")


@pytest.mark.django_db
def test_substitute_validation_and_decline_recovery():
    upsert_profile(
        {
            "user_id": 110,
            "category": "faculty",
            "designation": "Assistant Professor",
            "unit": "CSE",
            "unit_head_user_id": 210,
            "sanction_authority_user_id": 310,
        }
    )
    upsert_profile(
        {
            "user_id": 111,
            "category": "faculty",
            "designation": "Assistant Professor",
            "unit": "CSE",
            "unit_head_user_id": 210,
            "sanction_authority_user_id": 310,
        }
    )
    upsert_profile(
        {
            "user_id": 112,
            "category": "faculty",
            "designation": "Associate Professor",
            "unit": "CSE",
            "unit_head_user_id": 210,
            "sanction_authority_user_id": 310,
        }
    )
    allot_balance({"employee_id": 110, "category": "CL", "year": 2026, "allotted": Decimal("8.0")})
    allot_balance({"employee_id": 111, "category": "CL", "year": 2026, "allotted": Decimal("8.0")})

    with pytest.raises(ValidationError):
        submit(
            _principal(110),
            {
                "category": "CL",
                "start_date": date(2026, 10, 12),
                "end_date": date(2026, 10, 12),
                "reason": "Test",
                "substitute_user_id": 99999,
            },
        )

    sub_leave = submit(
        _principal(111),
        {
            "category": "CL",
            "start_date": date(2026, 10, 12),
            "end_date": date(2026, 10, 12),
            "reason": "Substitute own leave",
        },
    )
    assert sub_leave.status == "PENDING"

    with pytest.raises(ValidationError):
        submit(
            _principal(110),
            {
                "category": "CL",
                "start_date": date(2026, 10, 12),
                "end_date": date(2026, 10, 12),
                "reason": "Conflict test",
                "substitute_user_id": 111,
            },
        )

    app = submit(
        _principal(110),
        {
            "category": "CL",
            "start_date": date(2026, 10, 13),
            "end_date": date(2026, 10, 13),
            "reason": "Conference",
            "substitute_user_id": 111,
        },
    )
    assert app.status == "AWAITING_SUB"

    declined = decide(_principal(111), app.id, action="decline_substitute", remarks="Unavailable")
    assert declined.status == "ACTION_REQUIRED"
    assert declined.substitute_status == "DECLINED"

    with pytest.raises(ValidationError):
        nominate_replacement_substitute(_principal(110), app.id, 99999)

    replaced = nominate_replacement_substitute(_principal(110), app.id, 112)
    assert replaced.status == "AWAITING_SUB"
    assert replaced.substitute_user_id == 112
    assert replaced.substitute_status == "PENDING"

    accepted = decide(_principal(112), app.id, action="accept_substitute", remarks="Available")
    assert accepted.status == "PENDING"
    assert accepted.substitute_status == "ACCEPTED"


@pytest.mark.django_db
def test_higher_sanction_flow_and_not_recommended_behavior():
    upsert_profile(
        {
            "user_id": 120,
            "category": "faculty",
            "designation": "Assistant Professor",
            "unit": "ECE",
            "unit_head_user_id": 220,
            "sanction_authority_user_id": 320,
        }
    )
    allot_balance({"employee_id": 120, "category": "EL", "year": 2026, "allotted": Decimal("30.0")})

    app = submit(
        _principal(120),
        {
            "category": "EL",
            "start_date": date(2026, 11, 2),
            "end_date": date(2026, 11, 4),
            "reason": "Research visit",
        },
    )
    assert app.status == "PENDING"

    not_rec = decide(_principal(220), app.id, action="not_recommend", remarks="Heavy teaching load")
    assert not_rec.status == "RECOMMENDED"
    assert not_rec.recommendation == "NOT_RECOMMENDED"

    sanctioned = decide(_principal(320), app.id, action="approve", remarks="Approved despite note")
    assert sanctioned.status == "APPROVED"
    bal = LeaveBalance.objects.get(employee_id=120, year=2026, category="EL")
    assert bal.used == Decimal("3.0")


@pytest.mark.django_db
def test_establishment_routing_step():
    upsert_profile(
        {
            "user_id": 130,
            "category": "staff",
            "designation": "Junior Engineer",
            "unit": "Civil Works",
            "unit_head_user_id": 230,
            "establishment_user_id": 250,
            "sanction_authority_user_id": 330,
        }
    )
    allot_balance(
        {"employee_id": 130, "category": "SCL", "year": 2026, "allotted": Decimal("15.0")}
    )

    app = submit(
        _principal(130),
        {
            "category": "SCL",
            "start_date": date(2026, 10, 19),
            "end_date": date(2026, 10, 20),
            "reason": "Special Institute Assignment",
        },
    )
    assert app.status == "PENDING"

    uh_rec = decide(_principal(230), app.id, action="recommend", remarks="Recommended")
    assert uh_rec.status == "AWAITING_ESTABLISHMENT"

    with pytest.raises(PermissionDenied):
        decide(_principal(330), app.id, action="approve")

    routed = decide(_principal(250), app.id, action="verify_and_route", remarks="Verified records")
    assert routed.status == "RECOMMENDED"

    final = decide(_principal(330), app.id, action="approve", remarks="Sanctioned")
    assert final.status == "APPROVED"


@pytest.mark.django_db
def test_approved_leave_cancellation_workflow():
    upsert_profile(
        {
            "user_id": 140,
            "category": "staff",
            "designation": "Assistant",
            "unit": "Accounts",
            "unit_head_user_id": 240,
            "sanction_authority_user_id": 340,
        }
    )
    future_start = timezone.localdate() + timedelta(days=20)
    future_end = future_start + timedelta(days=2)
    while future_start.weekday() >= 5:
        future_start += timedelta(days=1)
        future_end = future_start + timedelta(days=2)

    allot_balance(
        {
            "employee_id": 140,
            "category": "CL",
            "year": future_start.year,
            "allotted": Decimal("8.0"),
        }
    )

    app = submit(
        _principal(140),
        {
            "category": "CL",
            "start_date": future_start,
            "end_date": future_end,
            "reason": "Personal work",
        },
    )
    decide(_principal(240), app.id, action="approve")
    bal = LeaveBalance.objects.get(employee_id=140, year=future_start.year, category="CL")
    used_initial = bal.used
    assert used_initial > 0

    req = request_cancellation(_principal(140), app.id, remarks="Family emergency resolved")
    assert req.status == "CANCELLATION_PENDING"
    bal.refresh_from_db()
    assert bal.used == used_initial

    rejected_cancel = decide(
        _principal(240), app.id, action="reject_cancellation", remarks="Too late to cancel"
    )
    assert rejected_cancel.status == "APPROVED"
    bal.refresh_from_db()
    assert bal.used == used_initial

    request_cancellation(_principal(140), app.id, remarks="Request again")
    approved_cancel = decide(
        _principal(240), app.id, action="approve_cancellation", remarks="Agreed"
    )
    assert approved_cancel.status == "CANCELLED"
    bal.refresh_from_db()
    assert bal.used == Decimal("0.0")


@pytest.mark.django_db
def test_leave_extension_workflow():
    upsert_profile(
        {
            "user_id": 150,
            "category": "faculty",
            "designation": "Professor",
            "unit": "Physics",
            "unit_head_user_id": 250,
            "sanction_authority_user_id": 350,
        }
    )
    today = timezone.localdate()
    allot_balance(
        {"employee_id": 150, "category": "EL", "year": today.year, "allotted": Decimal("30.0")}
    )

    base_app = submit(
        _principal(150),
        {
            "category": "EL",
            "start_date": today,
            "end_date": today + timedelta(days=2),
            "reason": "Conference",
        },
    )
    decide(_principal(250), base_app.id, action="recommend")
    decide(_principal(350), base_app.id, action="approve")
    base_app.refresh_from_db()
    assert base_app.status == "APPROVED"

    ext_app = submit_extension(
        _principal(150),
        base_app.id,
        {
            "end_date": today + timedelta(days=4),
            "reason": "Flight delayed, need 2 extra days",
        },
    )
    assert ext_app.status == "EXTENSION_PENDING"
    assert ext_app.extended_from_id == base_app.id
    assert ext_app.duration == Decimal("2.0")

    decided_ext = decide(
        _principal(250), ext_app.id, action="recommend", remarks="Extended leave recommended"
    )
    assert decided_ext.status == "EXTENSION_SANCTION"

    decide(_principal(350), ext_app.id, action="approve", remarks="Extension sanctioned")
    ext_app.refresh_from_db()
    assert ext_app.status == "APPROVED"

    bal = LeaveBalance.objects.get(employee_id=150, year=today.year, category="EL")
    assert bal.used == Decimal("5.0")


@pytest.mark.django_db
def test_duty_resumption_workflow():
    upsert_profile(
        {
            "user_id": 160,
            "category": "staff",
            "designation": "Technical Officer",
            "unit": "Computer Center",
            "unit_head_user_id": 260,
            "sanction_authority_user_id": 360,
        }
    )
    allot_balance({"employee_id": 160, "category": "EL", "year": 2026, "allotted": Decimal("30.0")})

    app = submit(
        _principal(160),
        {
            "category": "EL",
            "start_date": date(2026, 10, 5),
            "end_date": date(2026, 10, 9),
            "reason": "Personal",
        },
    )
    decide(_principal(260), app.id, action="recommend")
    decide(_principal(360), app.id, action="approve")
    bal = LeaveBalance.objects.get(employee_id=160, year=2026, category="EL")
    assert bal.used == Decimal("5.0")

    submit_resumption(
        _principal(160), app.id, actual_date=date(2026, 10, 7), remarks="Returned early"
    )
    app.refresh_from_db()
    assert app.status == "RESUMPTION_PENDING"

    review_resumption(_principal(360), app.id, remarks="Early return verified")
    app.refresh_from_db()
    assert app.status == "APPROVED"
    assert app.duration == Decimal("3.0")
    bal.refresh_from_db()
    assert bal.used == Decimal("3.0")


@pytest.mark.django_db
def test_retrospective_offline_sanction():
    upsert_profile(
        {
            "user_id": 170,
            "category": "faculty",
            "designation": "Associate Professor",
            "unit": "Design",
            "unit_head_user_id": 270,
            "sanction_authority_user_id": 370,
        }
    )
    allot_balance({"employee_id": 170, "category": "EL", "year": 2026, "allotted": Decimal("30.0")})

    with pytest.raises(ValidationError):
        record_offline_leave(
            _principal(999),
            {
                "employee_id": 170,
                "category": "EL",
                "start_date": date(2026, 8, 3),
                "end_date": date(2026, 8, 5),
                "sanction_reference": "",
            },
        )

    offline_app = record_offline_leave(
        _principal(999),
        {
            "employee_id": 170,
            "category": "EL",
            "start_date": date(2026, 8, 3),
            "end_date": date(2026, 8, 5),
            "sanction_reference": "DISP/2026/EL/042 signed by Registrar",
            "reason": "Offline approved medical leave",
        },
    )
    assert offline_app.status == "APPROVED"
    assert offline_app.is_offline is True
    assert offline_app.sanction_reference == "DISP/2026/EL/042 signed by Registrar"
    bal = LeaveBalance.objects.get(employee_id=170, year=2026, category="EL")
    assert bal.used == Decimal("3.0")


@pytest.mark.django_db
def test_automated_year_end_processing():
    upsert_profile(
        {
            "user_id": 180,
            "category": "faculty",
            "designation": "Professor",
            "unit": "Mathematics",
            "unit_head_user_id": 280,
            "sanction_authority_user_id": 380,
        }
    )
    allot_balance({"employee_id": 180, "category": "CL", "year": 2026, "allotted": Decimal("8.0")})
    allot_balance({"employee_id": 180, "category": "VL", "year": 2026, "allotted": Decimal("60.0")})
    allot_balance({"employee_id": 180, "category": "EL", "year": 2026, "allotted": Decimal("10.0")})

    cl = LeaveBalance.objects.get(employee_id=180, year=2026, category="CL")
    cl.used = Decimal("3.0")
    cl.save()

    vl = LeaveBalance.objects.get(employee_id=180, year=2026, category="VL")
    vl.used = Decimal("45.0")
    vl.save()

    summary = execute_year_end_processing(2026)
    assert summary["lapsed_records"] >= 1
    assert summary["vl_converted_faculty"] >= 1

    cl.refresh_from_db()
    assert cl.used == cl.allotted

    next_el = LeaveBalance.objects.get(employee_id=180, year=2027, category="EL")
    assert next_el.allotted == Decimal("17.5")


@pytest.mark.django_db
def test_sla_threshold_processing():
    upsert_profile(
        {
            "user_id": 190,
            "category": "staff",
            "designation": "Assistant",
            "unit": "Library",
            "unit_head_user_id": 290,
            "sanction_authority_user_id": 390,
        }
    )
    allot_balance({"employee_id": 190, "category": "CL", "year": 2026, "allotted": Decimal("8.0")})
    SlaConfig.objects.create(
        task_type="PENDING", reminder_hours=1, escalation_hours=2, escalate_to_user_id=390
    )

    app = submit(
        _principal(190),
        {
            "category": "CL",
            "start_date": date(2026, 10, 12),
            "end_date": date(2026, 10, 12),
            "reason": "Test SLA",
        },
    )
    app.created_at = timezone.now() - timedelta(hours=3)
    app.save(update_fields=["created_at"])

    report = process_sla_thresholds()
    assert report["reminded"] >= 1
    assert report["escalated"] >= 1
    assert LeaveNotification.objects.filter(application=app, is_reminder=True).exists()
    assert LeaveNotification.objects.filter(application=app, is_escalation=True).exists()


@pytest.mark.django_db
def test_printable_application_representation():
    upsert_profile(
        {
            "user_id": 195,
            "category": "faculty",
            "designation": "Assistant Professor",
            "unit": "ME",
            "unit_head_user_id": 295,
            "sanction_authority_user_id": 395,
        }
    )
    allot_balance({"employee_id": 195, "category": "CL", "year": 2026, "allotted": Decimal("8.0")})
    app = submit(
        _principal(195),
        {
            "category": "CL",
            "start_date": date(2026, 10, 12),
            "end_date": date(2026, 10, 12),
            "reason": "Personal matter",
        },
    )
    decide(_principal(295), app.id, action="approve", remarks="Approved by UH")
    fetched = get_accessible_application(195, app.id)
    assert fetched.id == app.id
    assert fetched.events.count() >= 2
    assert get_employee_leave_profiles([195])[0]["unit"] == "ME"
