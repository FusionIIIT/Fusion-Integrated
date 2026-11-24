from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.http import Http404
from rest_framework.exceptions import PermissionDenied, ValidationError

from modules.elm.models import LeaveApplication
from modules.elm.services.leave import allot_balance, decide, submit, upsert_profile, withdraw


def _p(uid: int):
    return SimpleNamespace(user_id=uid)


def _setup_sec(applicant=7501, uh=7502, sa=7503):
    for uid in (applicant, uh, sa):
        upsert_profile({
            "user_id": uid,
            "category": "faculty",
            "designation": "Assistant Professor",
            "unit": "CSE",
            "unit_head_user_id": uh,
            "sanction_authority_user_id": sa,
        })
    allot_balance({
        "employee_id": applicant,
        "category": "CL",
        "year": 2026,
        "allotted": Decimal("8.0"),
    })


def test_withdrawal_workflow(db):
    _setup_sec(7501, 7502, 7503)
    app = submit(
        _p(7501),
        {
            "category": "CL",
            "start_date": date(2026, 8, 3),
            "end_date": date(2026, 8, 4),
            "reason": "Test",
        },
    )
    assert app.status == "PENDING"
    withdrawn = withdraw(_p(7501), app.id)
    assert withdrawn.status == "WITHDRAWN"
    with pytest.raises(ValidationError):
        withdraw(_p(7501), app.id)


def test_sec_horizontal_privilege_escalation(db):
    _setup_sec(7511, 7512, 7513)
    upsert_profile({
        "user_id": 7599,
        "category": "faculty",
        "designation": "Assistant Professor",
        "unit": "ECE",
        "unit_head_user_id": 7512,
        "sanction_authority_user_id": 7513,
    })
    app = submit(
        _p(7511),
        {
            "category": "CL",
            "start_date": date(2026, 8, 10),
            "end_date": date(2026, 8, 11),
            "reason": "Test",
        },
    )
    with pytest.raises(Http404):
        withdraw(_p(7599), app.id)
    with pytest.raises(PermissionDenied):
        decide(_p(7599), app.id, action="approve")


def test_sec_applicant_cannot_approve_own_leave(db):
    _setup_sec(7521, 7522, 7523)
    app = submit(
        _p(7521),
        {
            "category": "CL",
            "start_date": date(2026, 8, 17),
            "end_date": date(2026, 8, 18),
            "reason": "Test",
        },
    )
    with pytest.raises(PermissionDenied):
        decide(_p(7521), app.id, action="approve")


def test_bnd_inverted_dates_rejected(db):
    _setup_sec(7531, 7532, 7533)
    with pytest.raises(ValidationError):
        submit(
            _p(7531),
            {
                "category": "CL",
                "start_date": date(2026, 9, 10),
                "end_date": date(2026, 9, 5),
                "reason": "Test",
            },
        )


def test_bnd_overlapping_leave_rejected(db):
    _setup_sec(7541, 7542, 7543)
    submit(
        _p(7541),
        {
            "category": "CL",
            "start_date": date(2026, 9, 14),
            "end_date": date(2026, 9, 16),
            "reason": "Test 1",
        },
    )
    with pytest.raises(ValidationError):
        submit(
            _p(7541),
            {
                "category": "CL",
                "start_date": date(2026, 9, 15),
                "end_date": date(2026, 9, 18),
                "reason": "Test 2",
            },
        )


def test_sec_special_characters_and_sql_injection_safe(db):
    _setup_sec(7551, 7552, 7553)
    payload = "<script>alert(1)</script>' OR '1'='1' -- DROP TABLE leave_application;"
    app = submit(
        _p(7551),
        {
            "category": "CL",
            "start_date": date(2026, 9, 21),
            "end_date": date(2026, 9, 22),
            "reason": payload,
        },
    )
    assert app.status == "PENDING"
    assert app.reason == payload
    assert LeaveApplication.objects.filter(pk=app.id).exists()
