from decimal import Decimal

import pytest

from modules.elm.models import LeaveUsage, SanctioningAuthorityRule
from modules.elm.services import (
    apply_leave,
    make_director_decision,
    make_final_decision,
    review_leave,
)

pytestmark = pytest.mark.django_db


def test_row_13_el_friday_monday_deducts_four(elm_people):
    SanctioningAuthorityRule.objects.create(category="EL", authority=elm_people[3])
    app = apply_leave(
        applicant=elm_people[0], category="EL", start_date="2026-01-02", end_date="2026-01-05"
    )
    review_leave(application=app, unit_head=elm_people[1], decision="Recommended")
    make_final_decision(application=app, actor=elm_people[3], decision="Approve")
    assert LeaveUsage.objects.get(
        employee=elm_people[0], category="EL", year=2026
    ).used_days == Decimal("4")


def test_row_14_reject_changes_nothing(elm_people):
    SanctioningAuthorityRule.objects.create(category="EL", authority=elm_people[3])
    app = apply_leave(
        applicant=elm_people[0], category="EL", start_date="2026-01-01", end_date="2026-01-01"
    )
    review_leave(application=app, unit_head=elm_people[1], decision="Recommended")
    make_final_decision(application=app, actor=elm_people[3], decision="Reject")
    assert not LeaveUsage.objects.filter(employee=elm_people[0], category="EL").exists()


def test_rows_15_16_director_self_sanction(elm_people):
    elm_people[0].is_director = True
    elm_people[0].save(update_fields=["is_director"])
    app = apply_leave(
        applicant=elm_people[0], category="CL", start_date="2026-01-01", end_date="2026-01-01"
    )
    assert (
        make_director_decision(application=app, actor=elm_people[0], decision="Reject").state
        == "Rejected"
    )
