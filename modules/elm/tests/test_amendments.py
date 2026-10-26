from decimal import Decimal

import pytest
from freezegun import freeze_time
from rest_framework.exceptions import ValidationError

from modules.elm.amendments import cancel_request
from modules.elm.decisions import decide
from modules.elm.models import LeaveBalance
from modules.elm.tests.test_submission import pending_context

pytestmark = pytest.mark.django_db


def approved_context():
    req, applicant, authority, leave_type = pending_context()
    decide(req.pk, authority, "APPROVE")
    req.refresh_from_db()
    return (req, applicant, authority, leave_type)


def test_approved_cancellation_restores_balance():
    base, applicant, authority, leave_type = approved_context()
    child = cancel_request(base.pk, applicant)
    base.refresh_from_db()
    assert base.status == "APPROVED"
    decide(child.pk, authority, "APPROVE")
    base.refresh_from_db()
    assert base.status == "CANCELLED"
    balance = LeaveBalance.objects.get(employee=101, leave_type=leave_type, year=2026)
    assert balance.balance == Decimal("8")


def test_rejected_cancellation_preserves_approved_leave():
    base, applicant, authority, leave_type = approved_context()
    child = cancel_request(base.pk, applicant)
    decide(child.pk, authority, "REJECT")
    base.refresh_from_db()
    assert base.status == "APPROVED"
    balance = LeaveBalance.objects.get(employee=101, leave_type=leave_type, year=2026)
    assert balance.balance == Decimal("7")


def test_cancellation_is_unavailable_on_start_date():
    base, applicant, _authority, _leave_type = approved_context()
    base.start_date = "2026-11-02"
    base.save()
    with freeze_time("2026-11-02"), pytest.raises(ValidationError):
        cancel_request(base.pk, applicant)
    base.refresh_from_db()
    assert base.status == "APPROVED"
