from datetime import date
from decimal import Decimal

import pytest
from freezegun import freeze_time
from rest_framework.exceptions import PermissionDenied, ValidationError

from conftest import make_principal
from modules.elm.amendments import extension_request, resumption_request
from modules.elm.decisions import decide
from modules.elm.models import AuthorityRoute, LeaveBalance
from modules.elm.tests.test_submission import seed
from modules.elm.workflows import submit

pytestmark = pytest.mark.django_db


def approved_el_context():
    leave_type, principal = seed()
    leave_type.type = "EL"
    leave_type.save()
    authority_route = AuthorityRoute.objects.get(employee=101)
    authority_route.higher_authorities = [301]
    authority_route.save()
    head = make_principal(
        user_id=201, kind="staff", modules=("elm",), permissions=("elm.leave_requests.approve",)
    )
    final = make_principal(
        user_id=301, kind="faculty", modules=("elm",), permissions=("elm.leave_requests.approve",)
    )
    base = submit(
        {
            "leave_type": leave_type,
            "start_date": date(2026, 11, 2),
            "end_date": date(2026, 11, 4),
            "purpose": "Family",
        },
        principal,
    )
    decide(base.pk, head, "RECOMMEND")
    decide(base.pk, final, "APPROVE")
    base.refresh_from_db()
    return base, principal, head, final, leave_type


def test_extension_charges_only_added_days():
    base, applicant, head, final, leave_type = approved_el_context()
    initial_balance = LeaveBalance.objects.get(
        employee=101, leave_type=leave_type, year=2026
    ).balance
    assert initial_balance == Decimal("27")
    with freeze_time("2026-11-03"):
        child = extension_request(base.pk, applicant, date(2026, 11, 6))
        assert child.start_date == date(2026, 11, 5)
        assert child.days == Decimal("2")
        assert LeaveBalance.objects.get(
            employee=101, leave_type=leave_type, year=2026
        ).balance == Decimal("27")
        decide(child.pk, head, "NOT_RECOMMEND")
        child.refresh_from_db()
        assert child.status == "PENDING"
        assert child.step == 1
        decide(child.pk, final, "APPROVE")
        assert LeaveBalance.objects.get(
            employee=101, leave_type=leave_type, year=2026
        ).balance == Decimal("25")
        base.refresh_from_db()
        assert base.end_date == date(2026, 11, 4)


@pytest.mark.parametrize("actual_day,expected", [(4, "27"), (3, "28"), (6, "25")])
def test_resumption_review_adjusts_only_after_review(actual_day, expected):
    base, applicant, head, final, leave_type = approved_el_context()
    with freeze_time("2026-11-08"):
        child = resumption_request(
            base.pk, applicant, date(2026, 11, actual_day), "Returned to duty"
        )
        assert child.route == [301]
        assert LeaveBalance.objects.get(
            employee=101, leave_type=leave_type, year=2026
        ).balance == Decimal("27")

        with pytest.raises(PermissionDenied):
            decide(child.pk, head, "APPROVE")

        decide(child.pk, final, "APPROVE")
        base.refresh_from_db()
        assert base.actual_return_date == date(2026, 11, actual_day)
        assert base.status == "APPROVED"
        assert base.end_date == date(2026, 11, 4)
        balance = LeaveBalance.objects.get(employee=101, leave_type=leave_type, year=2026).balance
        assert balance == Decimal(expected)

        with pytest.raises(ValidationError):
            decide(child.pk, final, "APPROVE")

        with pytest.raises(ValidationError):
            resumption_request(base.pk, applicant, date(2026, 11, actual_day), "Returned to duty")


def test_reviewed_resumption_prevents_new_extension():
    base, applicant, _head, final, _leave_type = approved_el_context()
    with freeze_time("2026-11-03"):
        child = resumption_request(base.pk, applicant, date(2026, 11, 3), "Returned early")
        decide(child.pk, final, "APPROVE")
        with pytest.raises(ValidationError):
            extension_request(base.pk, applicant, date(2026, 11, 6))


def test_late_resumption_cannot_overlap_another_request():
    base, applicant, _head, final, leave_type = approved_el_context()
    submit(
        {
            "leave_type": leave_type,
            "start_date": date(2026, 11, 5),
            "end_date": date(2026, 11, 6),
            "purpose": "Other leave",
        },
        applicant,
    )
    with freeze_time("2026-11-08"):
        child = resumption_request(base.pk, applicant, date(2026, 11, 6), "Returned late")
        with pytest.raises(ValidationError):
            decide(child.pk, final, "APPROVE")
    base.refresh_from_db()
    assert base.actual_return_date is None
    assert LeaveBalance.objects.get(
        employee=101, leave_type=leave_type, year=2026
    ).balance == Decimal("27")
