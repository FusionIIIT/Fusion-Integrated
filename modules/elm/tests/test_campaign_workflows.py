from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from rest_framework.exceptions import ValidationError

from modules.elm.models import LeaveAccountTransaction, LeaveBalance
from modules.elm.services.leave import (
    allot_balance,
    decide,
    nominate_replacement_substitute,
    record_offline_leave,
    request_cancellation,
    review_resumption,
    submit,
    submit_resumption,
    upsert_profile,
)


def _p(uid: int):
    return SimpleNamespace(user_id=uid)


def _setup_wf(applicant, uh=None, sa=None, sub=None, category="faculty", unit="CSE"):
    for uid in filter(None, [applicant, uh, sa, sub]):
        upsert_profile({
            "user_id": uid,
            "category": category,
            "designation": "Professor" if uid == sa else "Associate Professor",
            "unit": unit,
            "unit_head_user_id": uh,
            "sanction_authority_user_id": sa,
        })


def test_substitute_decline_and_renomination(db):
    _setup_wf(7601, uh=7604, sa=7605, sub=7602)
    _setup_wf(7603, uh=7604, sa=7605)
    allot_balance({"employee_id": 7601, "category": "CL", "year": 2026, "allotted": Decimal("8.0")})
    allot_balance({"employee_id": 7602, "category": "CL", "year": 2026, "allotted": Decimal("8.0")})
    allot_balance({"employee_id": 7603, "category": "CL", "year": 2026, "allotted": Decimal("8.0")})

    app = submit(
        _p(7601),
        {
            "category": "CL",
            "start_date": date(2026, 8, 3),
            "end_date": date(2026, 8, 4),
            "reason": "Test",
            "substitute_user_id": 7602,
        },
    )
    assert app.status == "AWAITING_SUB"

    decide(_p(7602), app.id, action="decline_substitute")
    app.refresh_from_db()
    assert app.status == "ACTION_REQUIRED"

    with pytest.raises(ValidationError):
        nominate_replacement_substitute(_p(7601), app.id, 7601)

    app = nominate_replacement_substitute(_p(7601), app.id, 7603)
    assert app.status == "AWAITING_SUB"

    decide(_p(7603), app.id, action="accept_substitute")
    app.refresh_from_db()
    assert app.status == "PENDING"


def test_multi_tier_higher_sanction_flow_el(db):
    _setup_wf(7611, uh=7612, sa=7614)
    allot_balance({"employee_id": 7611, "category": "EL", "year": 2026, "allotted": Decimal("30.0")})

    app = submit(
        _p(7611),
        {
            "category": "EL",
            "start_date": date(2026, 8, 3),
            "end_date": date(2026, 8, 5),
            "reason": "Visit",
        },
    )
    assert app.status == "PENDING"

    rec = decide(_p(7612), app.id, action="recommend", remarks="Recommended")
    assert rec.status == "RECOMMENDED"

    sanctioned = decide(_p(7614), app.id, action="approve", remarks="Approved")
    assert sanctioned.status == "APPROVED"

    bal = LeaveBalance.objects.get(employee_id=7611, year=2026, category="EL")
    assert bal.used == Decimal("3.0")
    assert LeaveAccountTransaction.objects.filter(employee_id=7611, transaction_type="DEBIT").exists()


def test_unit_head_rejection_no_debit(db):
    _setup_wf(7621, uh=7622, sa=7623)
    allot_balance({"employee_id": 7621, "category": "CL", "year": 2026, "allotted": Decimal("8.0")})

    app = submit(
        _p(7621),
        {
            "category": "CL",
            "start_date": date(2026, 8, 3),
            "end_date": date(2026, 8, 4),
            "reason": "Test",
        },
    )
    rejected = decide(_p(7622), app.id, action="reject", remarks="Rejected")
    assert rejected.status == "REJECTED"

    bal = LeaveBalance.objects.get(employee_id=7621, year=2026, category="CL")
    assert bal.used == Decimal("0.0")
    assert not LeaveAccountTransaction.objects.filter(employee_id=7621, transaction_type="DEBIT").exists()


def test_approved_leave_cancellation_restores_balance(db):
    _setup_wf(7631, uh=7632, sa=7633)
    allot_balance({"employee_id": 7631, "category": "CL", "year": 2026, "allotted": Decimal("8.0")})

    app = submit(
        _p(7631),
        {
            "category": "CL",
            "start_date": date(2026, 11, 2),
            "end_date": date(2026, 11, 3),
            "reason": "Future",
        },
    )
    decide(_p(7632), app.id, action="approve")

    bal = LeaveBalance.objects.get(employee_id=7631, year=2026, category="CL")
    assert bal.used == Decimal("2.0")

    req = request_cancellation(_p(7631), app.id, remarks="Cancel request")
    assert req.status == "CANCELLATION_PENDING"

    cancelled = decide(_p(7632), app.id, action="approve_cancellation", remarks="Agreed")
    assert cancelled.status == "CANCELLED"

    bal.refresh_from_db()
    assert bal.used == Decimal("0.0")
    assert LeaveAccountTransaction.objects.filter(employee_id=7631, transaction_type="CREDIT").exists()


def test_duty_resumption_early_return_restores_balance(db):
    _setup_wf(7641, uh=7642, sa=7643)
    allot_balance({"employee_id": 7641, "category": "EL", "year": 2026, "allotted": Decimal("30.0")})

    app = submit(
        _p(7641),
        {
            "category": "EL",
            "start_date": date(2026, 10, 5),
            "end_date": date(2026, 10, 9),
            "reason": "Personal",
        },
    )
    decide(_p(7642), app.id, action="recommend")
    decide(_p(7643), app.id, action="approve")

    bal = LeaveBalance.objects.get(employee_id=7641, year=2026, category="EL")
    assert bal.used == Decimal("5.0")

    submit_resumption(_p(7641), app.id, actual_date=date(2026, 10, 7), remarks="Returned early")
    review_resumption(_p(7643), app.id, remarks="Early return verified")

    app.refresh_from_db()
    assert app.status == "APPROVED"
    assert app.duration == Decimal("3.0")

    bal.refresh_from_db()
    assert bal.used == Decimal("3.0")
    assert LeaveAccountTransaction.objects.filter(employee_id=7641, transaction_type="CREDIT").exists()


def test_retrospective_offline_sanction(db):
    _setup_wf(7651, uh=7652, sa=7653)
    allot_balance({"employee_id": 7651, "category": "SCL", "year": 2026, "allotted": Decimal("15.0")})

    offline_app = record_offline_leave(
        _p(7650),
        {
            "employee_id": 7651,
            "category": "SCL",
            "start_date": date(2026, 4, 1),
            "end_date": date(2026, 4, 2),
            "sanction_reference": "PAPER-REF-7651",
            "reason": "Paper leave",
        },
    )
    assert offline_app.status == "APPROVED"
    assert offline_app.is_offline is True
    assert offline_app.sanction_reference == "PAPER-REF-7651"

    bal = LeaveBalance.objects.get(employee_id=7651, year=2026, category="SCL")
    assert bal.used == Decimal("2.0")
    assert LeaveAccountTransaction.objects.filter(employee_id=7651, transaction_type="DEBIT").exists()
