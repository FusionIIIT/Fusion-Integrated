"""Regression coverage for the Unit Head recommendation business rule."""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework.exceptions import ValidationError

from conftest import make_principal
from modules.leave.models import LeaveApplication, LeaveDecision
from modules.leave.services import applications

pytestmark = pytest.mark.django_db


@pytest.fixture
def unit_head():
    return make_principal(
        user_id=303,
        kind="staff",
        active_role="Unit Head",
        roles=("Unit Head",),
        permissions=("leave.application.review",),
    )


@pytest.fixture
def higher_leave():
    return LeaveApplication.objects.create(
        applicant_user_id=101,
        leave_type="EL",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 3),
        requested_days=Decimal("3"),
        status="awaiting_unit_head_review",
        unit_head_user_id=303,
        final_authority_user_id=404,
        purpose="Family leave",
    )


@pytest.mark.parametrize(
    ("outcome", "expected"),
    [("recommended", "Recommended"), ("not_recommended", "Not Recommended")],
)
def test_recommendation_is_derived_from_explicit_outcome(
    unit_head,
    higher_leave,
    outcome,
    expected,
):
    updated = applications.act_on_application(
        unit_head,
        higher_leave,
        event="unit_head_decision",
        outcome=outcome,
        note="Independent review notes",
    )

    updated.refresh_from_db()
    assert updated.recommendation == expected
    assert updated.status == "awaiting_final_sanction_decision"
    decision = LeaveDecision.objects.get(application=higher_leave)
    assert decision.note == "Independent review notes"


@pytest.mark.parametrize("outcome", ["", "approve", "reject"])
def test_higher_leave_requires_valid_recommendation(unit_head, higher_leave, outcome):
    with pytest.raises(ValidationError):
        applications.act_on_application(
            unit_head,
            higher_leave,
            event="unit_head_decision",
            outcome=outcome,
        )
    higher_leave.refresh_from_db()
    assert higher_leave.status == "awaiting_unit_head_review"
    assert not LeaveDecision.objects.filter(application=higher_leave).exists()


@pytest.mark.parametrize("outcome", ["", "recommended", "not_recommended"])
def test_cl_decision_rejects_missing_or_unrelated_outcomes(unit_head, higher_leave, outcome):
    higher_leave.leave_type = "CL"
    higher_leave.save(update_fields=["leave_type"])
    with pytest.raises(ValidationError):
        applications.act_on_application(
            unit_head,
            higher_leave,
            event="unit_head_decision",
            outcome=outcome,
        )
    higher_leave.refresh_from_db()
    assert higher_leave.status == "awaiting_unit_head_review"
