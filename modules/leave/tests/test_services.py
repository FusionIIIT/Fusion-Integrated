"""Integration tests for leave services."""
import datetime
from decimal import Decimal
import pytest

from core.api.exceptions import ConflictError
from modules.leave.models import LeaveBalance, LeaveApplication, SubstituteRequest
from modules.leave.services import (
    apply_for_leave,
    withdraw_application,
    request_cancellation,
    respond_to_substitute_request,
    review_by_unit_head,
    sanction_application,
    process_cancellation_decision,
    submit_resumption_declaration,
    review_resumption_declaration,
    run_year_end_processing,
)


@pytest.mark.django_db
def test_apply_and_unit_head_approve_cl():
    user_id = 101
    start = datetime.date(2026, 11, 2)  # Monday
    end = datetime.date(2026, 11, 3)    # Tuesday

    # Initialize balance
    bal = LeaveBalance.objects.create(user_id=user_id, year=2026, cl_balance=Decimal("8.0"))

    app = apply_for_leave(
        user_id=user_id,
        category="CL",
        start_date=start,
        end_date=end,
        purpose="Personal work",
    )
    assert app.status == "under_review"
    assert app.days_count == Decimal("2.0")

    # Unit head review (CL: Unit Head is final)
    reviewed = review_by_unit_head(
        reviewer_user_id=201,
        application_id=app.pk,
        recommended=True,
        remarks="Approved",
    )
    assert reviewed.status == "approved"

    bal.refresh_from_db()
    assert bal.cl_balance == Decimal("6.0")  # 8 - 2 = 6


@pytest.mark.django_db
def test_substitute_workflow_and_higher_sanction_el():
    applicant_id = 102
    substitute_id = 103
    start = datetime.date(2026, 11, 2)
    end = datetime.date(2026, 11, 6)

    bal = LeaveBalance.objects.create(user_id=applicant_id, year=2026, el_balance=Decimal("30.0"))

    app = apply_for_leave(
        user_id=applicant_id,
        category="EL",
        start_date=start,
        end_date=end,
        purpose="Family event",
        substitute_user_id=substitute_id,
        responsibilities="Handle office inquiries",
    )
    assert app.status == "substitute_pending"

    # Substitute accepts
    sub_req = SubstituteRequest.objects.get(application=app)
    respond_to_substitute_request(
        substitute_user_id=substitute_id,
        request_id=sub_req.pk,
        decision="accepted",
        remarks="Will cover",
    )

    app.refresh_from_db()
    assert app.status == "under_review"

    # Unit Head recommends (EL: Unit head does NOT make final decision)
    review_by_unit_head(
        reviewer_user_id=201,
        application_id=app.pk,
        recommended=True,
        remarks="Recommended to Dean",
    )

    app.refresh_from_db()
    assert app.status == "under_review"
    assert app.unit_head_recommended is True

    # Dean / Sanctioning authority sanctions
    sanction_application(
        sanctioner_user_id=301,
        application_id=app.pk,
        decision="approved",
        remarks="Sanctioned",
    )

    app.refresh_from_db()
    assert app.status == "approved"

    bal.refresh_from_db()
    assert bal.el_balance == Decimal("25.0")  # 30 - 5 = 25


@pytest.mark.django_db
def test_withdrawal_before_approval():
    user_id = 104
    start = datetime.date(2026, 11, 9)
    end = datetime.date(2026, 11, 10)

    LeaveBalance.objects.create(user_id=user_id, year=2026, cl_balance=Decimal("8.0"))
    app = apply_for_leave(
        user_id=user_id,
        category="CL",
        start_date=start,
        end_date=end,
        purpose="Medical checkup",
    )
    assert app.status == "under_review"

    withdrawn = withdraw_application(user_id=user_id, application_id=app.pk, reason="Plans changed")
    assert withdrawn.status == "withdrawn"


@pytest.mark.django_db
def test_resumption_early_return_adjusts_balance():
    user_id = 105
    start = datetime.date(2026, 11, 2)
    end = datetime.date(2026, 11, 6)  # 5 days approved

    bal = LeaveBalance.objects.create(user_id=user_id, year=2026, el_balance=Decimal("30.0"))
    app = apply_for_leave(
        user_id=user_id,
        category="EL",
        start_date=start,
        end_date=end,
        purpose="Conference travel",
    )
    sanction_application(sanctioner_user_id=301, application_id=app.pk, decision="approved")

    bal.refresh_from_db()
    assert bal.el_balance == Decimal("25.0")  # deducted 5 days

    # Early resumption: returns on Nov 5 instead of after Nov 6 (resumed on Nov 5, availed Nov 2-4 = 3 days)
    resumed = submit_resumption_declaration(
        user_id=user_id,
        application_id=app.pk,
        resumption_date=datetime.date(2026, 11, 5),
    )
    assert resumed.status == "resumption_submitted"

    review_resumption_declaration(reviewer_user_id=301, application_id=app.pk)
    resumed.refresh_from_db()
    assert resumed.status == "closed"

    bal.refresh_from_db()
    # 2 unused days restored: 25 + 2 = 27
    assert bal.el_balance == Decimal("27.0")
