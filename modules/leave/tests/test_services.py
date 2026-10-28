import pytest
from datetime import date, timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from modules.leave.models import (
    LeaveApplication,
    LeaveCategory,
    LeaveStatus,
    SubstituteStatus,
    UnitHeadRecommendation,
    LeaveBalance,
)
from modules.leave.services.ledger import (
    credit_annual_entitlements,
    debit_balance,
    refund_balance,
    convert_vl_to_el,
    ensure_balance,
)
from modules.leave.services.workflow import (
    submit_application,
    respond_substitute,
    unit_head_review,
    sanction_decision,
    withdraw_application,
    cancel_approved_leave,
    submit_resumption,
)


@pytest.mark.django_db
def test_annual_entitlement_crediting_and_vl_conversion():
    user_id = 201
    year = 2026

    # Credit faculty entitlements
    balances = credit_annual_entitlements(user_id, year, is_faculty=True)
    assert balances[LeaveCategory.CL] == 8.0
    assert balances[LeaveCategory.RH] == 2.0
    assert balances[LeaveCategory.SCL] == 15.0
    assert balances[LeaveCategory.VL] == 60.0
    assert balances[LeaveCategory.COL] == 20.0

    # Simulate availing 20 days of VL -> 40 days remain
    debit_balance(user_id, year, LeaveCategory.VL, Decimal("20.0"))
    vl_bal = LeaveBalance.objects.get(user_id=user_id, year=year, category=LeaveCategory.VL)
    assert vl_bal.available_balance == 40.0

    # Year-end conversion of 40 VL at 2:1 -> 20 EL in next year
    unavailed, converted = convert_vl_to_el(user_id, year)
    assert unavailed == Decimal("40.0")
    assert converted == Decimal("20.0")

    next_el = LeaveBalance.objects.get(user_id=user_id, year=year + 1, category=LeaveCategory.EL)
    assert next_el.credited == Decimal("20.0")


@pytest.mark.django_db
def test_cl_full_approval_workflow():
    applicant_id = 301
    substitute_id = 302
    unit_head_id = 303
    year = 2026

    credit_annual_entitlements(applicant_id, year)

    # 1. Create and submit CL application with substitute
    app = LeaveApplication(
        user_id=applicant_id,
        category=LeaveCategory.CL,
        start_date=date(2026, 11, 23),
        end_date=date(2026, 11, 24),
        reason="Personal work",
        substitute_id=substitute_id,
        unit_head_id=unit_head_id,
    )
    submit_application(app, actor_id=applicant_id)
    assert app.status == LeaveStatus.SUBSTITUTE_PENDING
    assert app.substitute_status == SubstituteStatus.PENDING

    # 2. Substitute accepts
    respond_substitute(app, actor_id=substitute_id, accept=True, remarks="Will cover classes")
    assert app.status == LeaveStatus.UNIT_HEAD_PENDING
    assert app.substitute_status == SubstituteStatus.ACCEPTED

    # 3. Unit Head sanctions CL (final authority under BR-EL-016)
    unit_head_review(app, actor_id=unit_head_id, approve_or_recommend=True, remarks="Approved")
    assert app.status == LeaveStatus.APPROVED

    # Verify balance was debited (CL was 8.0, 2 days debited -> 6.0)
    bal = LeaveBalance.objects.get(user_id=applicant_id, year=year, category=LeaveCategory.CL)
    assert bal.available_balance == 6.0


@pytest.mark.django_db
def test_el_higher_sanction_workflow():
    applicant_id = 401
    unit_head_id = 402
    director_id = 403
    year = 2026

    # Give applicant EL balance
    ensure_balance(applicant_id, year, LeaveCategory.EL, default_credited=Decimal("30.0"))

    # 1. Submit EL application without substitute
    app = LeaveApplication(
        user_id=applicant_id,
        category=LeaveCategory.EL,
        start_date=date(2026, 11, 20),
        end_date=date(2026, 11, 24),
        reason="Family function",
        unit_head_id=unit_head_id,
        sanctioning_authority_id=director_id,
    )
    submit_application(app, actor_id=applicant_id)
    assert app.status == LeaveStatus.UNIT_HEAD_PENDING

    # 2. Unit Head reviews and records RECOMMENDED (not final sanction under BR-EL-017)
    unit_head_review(app, actor_id=unit_head_id, approve_or_recommend=True, remarks="Forwarded with recommendation")
    assert app.status == LeaveStatus.SANCTIONING_PENDING
    assert app.unit_head_recommendation == UnitHeadRecommendation.RECOMMENDED

    # 3. Director sanctions (final decision under BR-EL-018)
    sanction_decision(app, actor_id=director_id, approve=True, remarks="Sanctioned")
    assert app.status == LeaveStatus.APPROVED

    # Check balance debited (5 calendar days continuous count)
    bal = LeaveBalance.objects.get(user_id=applicant_id, year=year, category=LeaveCategory.EL)
    assert bal.available_balance == 25.0


@pytest.mark.django_db
def test_withdrawal_and_cancellation():
    applicant_id = 501
    unit_head_id = 502
    year = 2026

    credit_annual_entitlements(applicant_id, year)

    # Test immediate withdrawal while pending (BR-EL-022)
    app1 = LeaveApplication(
        user_id=applicant_id,
        category=LeaveCategory.CL,
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 1),
        reason="Doctor visit",
        unit_head_id=unit_head_id,
    )
    submit_application(app1, actor_id=applicant_id)
    assert app1.status == LeaveStatus.UNIT_HEAD_PENDING

    withdraw_application(app1, actor_id=applicant_id)
    assert app1.status == LeaveStatus.WITHDRAWN

    # Test cancellation of approved leave before start (BR-EL-023)
    app2 = LeaveApplication(
        user_id=applicant_id,
        category=LeaveCategory.CL,
        start_date=date(2026, 12, 10),
        end_date=date(2026, 12, 11),
        reason="Conference",
        unit_head_id=unit_head_id,
    )
    submit_application(app2, actor_id=applicant_id)
    unit_head_review(app2, actor_id=unit_head_id, approve_or_recommend=True)
    assert app2.status == LeaveStatus.APPROVED

    # Balance debited
    bal_before = LeaveBalance.objects.get(user_id=applicant_id, year=year, category=LeaveCategory.CL).available_balance
    assert bal_before == 6.0

    # Cancel approved leave -> restores 2 days
    cancel_approved_leave(app2, actor_id=applicant_id, reason="Conference cancelled")
    assert app2.status == LeaveStatus.CANCELLED

    bal_after = LeaveBalance.objects.get(user_id=applicant_id, year=year, category=LeaveCategory.CL).available_balance
    assert bal_after == 8.0


@pytest.mark.django_db
def test_ledger_positive_days_and_workflow_guards():
    user_id = 505
    year = 2026
    credit_annual_entitlements(user_id, year)

    # 1. Non-positive days to debit/refund
    with pytest.raises(ValidationError) as exc1:
        debit_balance(user_id, year, LeaveCategory.CL, Decimal("0.0"))
    assert "days" in exc1.value.message_dict

    with pytest.raises(ValidationError) as exc2:
        refund_balance(user_id, year, LeaveCategory.CL, Decimal("-1.0"))
    assert "days" in exc2.value.message_dict

    # 2. Resumption missing date or before leave start date
    app = LeaveApplication.objects.create(
        user_id=user_id,
        category=LeaveCategory.CL,
        start_date=date(2026, 12, 15),
        end_date=date(2026, 12, 16),
        calculated_days=Decimal("2.0"),
        status=LeaveStatus.APPROVED,
    )
    with pytest.raises(ValidationError) as exc_missing:
        submit_resumption(app, actor_id=user_id, actual_date=None)
    assert "actual_resumption_date" in exc_missing.value.message_dict

    with pytest.raises(ValidationError) as exc3:
        submit_resumption(app, actor_id=user_id, actual_date=date(2026, 12, 14))
    assert "actual_resumption_date" in exc3.value.message_dict

    # 3. Cancellation without reason
    with pytest.raises(ValidationError) as exc4:
        cancel_approved_leave(app, actor_id=user_id, reason="   ")
    assert "reason" in exc4.value.message_dict
