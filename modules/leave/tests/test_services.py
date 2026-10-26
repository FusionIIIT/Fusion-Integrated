"""Integration tests for leave services."""

import datetime
from decimal import Decimal

import pytest

from core.api.exceptions import NotFoundError
from modules.leave.models import LeaveBalance, SubstituteRequest
from modules.leave.services import (
    apply_for_leave,
    re_nominate_substitute,
    respond_to_substitute_request,
    review_by_unit_head,
    review_resumption_declaration,
    sanction_application,
    submit_resumption_declaration,
    withdraw_application,
)


@pytest.mark.django_db
def test_apply_and_unit_head_approve_cl():
    user_id = 101
    start = datetime.date(2026, 11, 2)  # Monday
    end = datetime.date(2026, 11, 3)  # Tuesday

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
def test_substitute_workflow_and_higher_sanction_el(stub_iam, user_ref):
    applicant_id = 102
    substitute_id = 103
    stub_iam(users={substitute_id: user_ref(substitute_id, kind="staff")})
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
def test_declined_substitute_requires_replacement_before_review(stub_iam, user_ref):
    applicant_id, first_substitute_id, replacement_id = 112, 113, 114
    stub_iam(
        users={
            first_substitute_id: user_ref(first_substitute_id, kind="staff"),
            replacement_id: user_ref(replacement_id, kind="faculty"),
        }
    )
    LeaveBalance.objects.create(user_id=applicant_id, year=2026, el_balance=Decimal("30.0"))
    app = apply_for_leave(
        user_id=applicant_id,
        category="EL",
        start_date=datetime.date(2026, 11, 16),
        end_date=datetime.date(2026, 11, 17),
        purpose="Substitute state regression",
        substitute_user_id=first_substitute_id,
    )
    first_request = SubstituteRequest.objects.get(application=app)

    respond_to_substitute_request(
        substitute_user_id=first_substitute_id,
        request_id=first_request.pk,
        decision="declined",
    )
    app.refresh_from_db()
    assert app.status == "applicant_action_required"

    replacement_request = re_nominate_substitute(
        user_id=applicant_id,
        application_id=app.pk,
        new_substitute_user_id=replacement_id,
    )
    app.refresh_from_db()
    assert app.status == "substitute_pending"
    assert not SubstituteRequest.objects.get(pk=first_request.pk).is_current

    with pytest.raises(NotFoundError):
        respond_to_substitute_request(
            substitute_user_id=first_substitute_id,
            request_id=first_request.pk,
            decision="accepted",
        )
    app.refresh_from_db()
    assert app.status == "substitute_pending"

    respond_to_substitute_request(
        substitute_user_id=replacement_id,
        request_id=replacement_request.pk,
        decision="accepted",
    )
    app.refresh_from_db()
    assert app.status == "under_review"


@pytest.mark.django_db
def test_substitute_cannot_revive_withdrawn_application(stub_iam, user_ref):
    applicant_id, substitute_id = 115, 116
    stub_iam(users={substitute_id: user_ref(substitute_id, kind="staff")})
    LeaveBalance.objects.create(user_id=applicant_id, year=2026, el_balance=Decimal("30.0"))
    app = apply_for_leave(
        user_id=applicant_id,
        category="EL",
        start_date=datetime.date(2026, 11, 18),
        end_date=datetime.date(2026, 11, 19),
        purpose="Withdrawn request regression",
        substitute_user_id=substitute_id,
    )
    sub_request = SubstituteRequest.objects.get(application=app)

    withdrawn = withdraw_application(user_id=applicant_id, application_id=app.pk)
    assert withdrawn.status == "withdrawn"
    assert not SubstituteRequest.objects.get(pk=sub_request.pk).is_current

    with pytest.raises(NotFoundError):
        respond_to_substitute_request(
            substitute_user_id=substitute_id,
            request_id=sub_request.pk,
            decision="accepted",
        )
    app.refresh_from_db()
    assert app.status == "withdrawn"


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
    assert resumed.status == "resumption_reviewed_early"

    bal.refresh_from_db()
    # 2 unused days restored: 25 + 2 = 27
    assert bal.el_balance == Decimal("27.0")


@pytest.mark.django_db
def test_resumption_on_first_leave_day_restores_all_days():
    user_id = 106
    start = datetime.date(2026, 11, 2)
    end = datetime.date(2026, 11, 6)
    balance = LeaveBalance.objects.create(user_id=user_id, year=2026, el_balance=Decimal("30.0"))
    app = apply_for_leave(
        user_id=user_id,
        category="EL",
        start_date=start,
        end_date=end,
        purpose="Return on the first day",
    )
    sanction_application(sanctioner_user_id=301, application_id=app.pk, decision="approved")

    submit_resumption_declaration(
        user_id=user_id,
        application_id=app.pk,
        resumption_date=start,
    )
    reviewed = review_resumption_declaration(reviewer_user_id=301, application_id=app.pk)

    balance.refresh_from_db()
    assert reviewed.actual_days_count == Decimal("0.0")
    assert reviewed.status == "resumption_reviewed_early"
    assert balance.el_balance == Decimal("30.0")


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("resumption_date", "expected_status", "expected_balance"),
    [
        (datetime.date(2026, 11, 6), "resumption_reviewed_normal", Decimal("25.0")),
        (datetime.date(2026, 11, 8), "resumption_reviewed_late", Decimal("24.0")),
    ],
)
def test_resumption_normal_and_late_outcomes(resumption_date, expected_status, expected_balance):
    user_id = 107
    start = datetime.date(2026, 11, 2)
    end = datetime.date(2026, 11, 6)
    balance = LeaveBalance.objects.create(user_id=user_id, year=2026, el_balance=Decimal("30.0"))
    app = apply_for_leave(
        user_id=user_id,
        category="EL",
        start_date=start,
        end_date=end,
        purpose="Resumption outcome regression coverage",
    )
    sanction_application(sanctioner_user_id=301, application_id=app.pk, decision="approved")
    submit_resumption_declaration(
        user_id=user_id,
        application_id=app.pk,
        resumption_date=resumption_date,
    )

    reviewed = review_resumption_declaration(reviewer_user_id=301, application_id=app.pk)

    balance.refresh_from_db()
    assert reviewed.status == expected_status
    assert balance.el_balance == expected_balance
