"""Tests for ELM Service layer."""
from datetime import date
from decimal import Decimal

import pytest

from modules.elm.domain.errors import (
    ElmDomainError,
    IllegalStateTransitionError,
    InsufficientLeaveBalanceError,
)
from modules.elm.models import LeaveApplication, LeaveCategory
from modules.elm.services import applications as svc

pytestmark = pytest.mark.django_db


@pytest.fixture
def categories():
    svc.ensure_leave_categories()
    return {c.code: c for c in LeaveCategory.objects.all()}


def test_submit_cl_application_success(categories):
    app = svc.submit_leave_application(
        user_id=1001,
        category_code="CL",
        start_date=date(2026, 11, 2),  # Monday
        end_date=date(2026, 11, 3),    # Tuesday
        reason="Personal work",
    )
    assert app.status == LeaveApplication.STATUS_SUBMITTED
    assert app.days_count == Decimal("2.0")
    assert app.history.count() == 1
    assert app.history.first().action == "submitted"


def test_submit_with_substitute(categories):
    app = svc.submit_leave_application(
        user_id=1001,
        category_code="CL",
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 2),
        reason="Doctor visit",
        substitute_id=2002,
    )
    assert app.status == LeaveApplication.STATUS_PENDING_SUBSTITUTE
    assert app.substitute_status == "pending"

    # Substitute accepts
    app = svc.respond_substitute(app.id, substitute_id=2002, action="accept")
    assert app.status == LeaveApplication.STATUS_SUBMITTED
    assert app.substitute_status == "accepted"


def test_substitute_decline(categories):
    app = svc.submit_leave_application(
        user_id=1001,
        category_code="CL",
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 2),
        reason="Doctor visit",
        substitute_id=2002,
    )
    app = svc.respond_substitute(app.id, substitute_id=2002, action="decline", remarks="Busy")
    assert app.status == LeaveApplication.STATUS_PENDING_SUBSTITUTE
    assert app.substitute_status == "declined"


def test_unit_head_approves_cl_and_deducts_balance(categories):
    cl = categories["CL"]
    bal = svc.get_or_create_balance(1001, cl, year=2026)
    initial_bal = bal.balance

    app = svc.submit_leave_application(
        user_id=1001,
        category_code="CL",
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 3),
        reason="Personal work",
    )
    # Unit head approves CL
    app = svc.review_unit_head(app.id, actor_id=9001, action="approve", remarks="Approved")
    assert app.status == LeaveApplication.STATUS_APPROVED
    assert app.unit_head_recommendation == "recommended"

    bal.refresh_from_db()
    assert bal.consumed == Decimal("2.0")
    assert bal.balance == initial_bal - Decimal("2.0")


def test_higher_sanction_flow_el(categories):
    el = categories["EL"]
    bal = svc.get_or_create_balance(1001, el, year=2026)
    initial_bal = bal.balance

    app = svc.submit_leave_application(
        user_id=1001,
        category_code="EL",
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 6),
        reason="Family trip",
    )
    # Unit head recommends
    app = svc.review_unit_head(app.id, actor_id=9001, action="recommend", remarks="Recommended")
    assert app.status == LeaveApplication.STATUS_PENDING_SANCTION
    assert app.unit_head_recommendation == "recommended"

    # Balance not deducted yet
    bal.refresh_from_db()
    assert bal.consumed == Decimal("0.0")

    # Sanctioning authority approves
    app = svc.review_sanctioning_authority(
        app.id, actor_id=9999, action="approve", remarks="Final approval"
    )
    assert app.status == LeaveApplication.STATUS_APPROVED

    bal.refresh_from_db()
    assert bal.consumed == Decimal("5.0")
    assert bal.balance == initial_bal - Decimal("5.0")


def test_applicant_withdraw(categories):
    app = svc.submit_leave_application(
        user_id=1001,
        category_code="CL",
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 2),
        reason="Personal work",
    )
    app = svc.withdraw_application(app.id, user_id=1001, remarks="Plans cancelled")
    assert app.status == LeaveApplication.STATUS_WITHDRAWN

    # Cannot withdraw someone else's application
    with pytest.raises(ElmDomainError, match="Only the applicant"):
        svc.withdraw_application(app.id, user_id=2002)


def test_cannot_withdraw_approved_leave(categories):
    app = svc.submit_leave_application(
        user_id=1001,
        category_code="CL",
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 2),
        reason="Personal work",
    )
    svc.review_unit_head(app.id, actor_id=9001, action="approve")

    with pytest.raises(IllegalStateTransitionError):
        svc.withdraw_application(app.id, user_id=1001)


def test_insufficient_balance_prevents_submit(categories):
    cl = categories["CL"]
    bal = svc.get_or_create_balance(1001, cl, year=2026)
    bal.balance = Decimal("1.0")
    bal.save()

    with pytest.raises(InsufficientLeaveBalanceError):
        svc.submit_leave_application(
            user_id=1001,
            category_code="CL",
            start_date=date(2026, 11, 2),
            end_date=date(2026, 11, 4),  # 3 days
            reason="Personal work",
        )
