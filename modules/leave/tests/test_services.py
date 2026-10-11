import datetime
from decimal import Decimal

import pytest

from core.api.exceptions import ConflictError
from modules.leave.domain.state_machine import LeaveState
from modules.leave.models import (
    AuthorityRule,
    Calendar,
    CategoryRule,
    Holiday,
    LeaveRequest,
    LedgerEntry,
    Policy,
    SlaClock,
    SlaRule,
)
from modules.leave.selectors.balances import get_user_balance
from modules.leave.services import (
    apply,
    cancel,
    resumption,
    review,
    routing,
    sanction,
    sla,
    substitute,
    withdraw,
    yearend,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def leave_setup():
    year = 2026
    cal = Calendar.objects.create(year=year, version="1.0", published=True)
    Holiday.objects.create(calendar=cal, day=datetime.date(year, 1, 26), name="Republic Day", restricted=False)

    policy = Policy.objects.create(
        version="2026.1",
        effective_from=datetime.date(year, 1, 1),
        effective_to=datetime.date(year, 12, 31),
        published=True,
    )

    CategoryRule.objects.create(
        policy=policy, category="CL", annual_credit=Decimal("8.0"), applies_to_faculty=True
    )
    CategoryRule.objects.create(
        policy=policy, category="EL", annual_credit=Decimal("30.0"), carries_forward=True, applies_to_faculty=True
    )
    CategoryRule.objects.create(
        policy=policy, category="VL", annual_credit=Decimal("60.0"), applies_to_faculty=True
    )

    AuthorityRule.objects.create(
        policy=policy, category="CL", sanctioning_designation="Unit Head", applies_to_faculty=True
    )
    AuthorityRule.objects.create(
        policy=policy, category="EL", establishment_step=True, sanctioning_designation="Dean", applies_to_faculty=True
    )

    # Initial ledger balance credits for test user 100
    LedgerEntry.objects.create(user_id=100, year=year, category="CL", days=Decimal("8.0"), reason="initial_credit")
    LedgerEntry.objects.create(user_id=100, year=year, category="EL", days=Decimal("30.0"), reason="initial_credit")
    LedgerEntry.objects.create(user_id=100, year=year, category="VL", days=Decimal("60.0"), reason="initial_credit")

    return {"calendar": cal, "policy": policy}


def test_submit_casual_leave_and_unit_head_approval(leave_setup):
    user_id = 100
    starts = datetime.date(2026, 1, 5) # Monday
    ends = datetime.date(2026, 1, 6) # Tuesday

    # 1. Submit CL
    req = apply.submit_leave_request(
        user_id=user_id,
        category="CL",
        starts_on=starts,
        ends_on=ends,
        reason="Family function",
    )
    assert req.state == LeaveState.PENDING_REVIEW
    assert req.requested_days == Decimal("2.0")

    # 2. Unit Head reviews and approves CL (final authority)
    decided_req = review.review_leave_request(
        request_id=req.id,
        reviewer_user_id=999,
        reviewer_role="Unit Head",
        approve=True,
        remark="Approved",
    )
    assert decided_req.state == LeaveState.APPROVED

    # Check ledger balance is debited by 2.0 days
    bal = get_user_balance(user_id, 2026, "CL")
    assert bal == Decimal("6.0")


def test_submit_insufficient_balance_fails(leave_setup):
    user_id = 100
    # Request more CL than 8.0 available
    starts = datetime.date(2026, 1, 5)
    ends = datetime.date(2026, 1, 20)
    with pytest.raises(ConflictError):
        apply.submit_leave_request(
            user_id=user_id,
            category="CL",
            starts_on=starts,
            ends_on=ends,
            reason="Exceeding quota",
        )


def test_earned_leave_full_hierarchy_with_substitute(leave_setup):
    user_id = 100
    substitute_id = 101
    starts = datetime.date(2026, 2, 2)
    ends = datetime.date(2026, 2, 6)

    # 1. Submit EL with substitute
    req = apply.submit_leave_request(
        user_id=user_id,
        category="EL",
        starts_on=starts,
        ends_on=ends,
        reason="Vacation trip",
        substitute_user_id=substitute_id,
    )
    assert req.state == LeaveState.SUBMITTED_PENDING_SUBSTITUTE

    # 2. Substitute accepts
    req = substitute.respond_substitute_nomination(
        request_id=req.id,
        substitute_user_id=substitute_id,
        accepted=True,
        remark="I agree to stand in",
    )
    assert req.state == LeaveState.PENDING_REVIEW

    # 3. Unit Head recommends
    req = review.review_leave_request(
        request_id=req.id,
        reviewer_user_id=200,
        reviewer_role="Unit Head",
        approve=True,
        remark="Recommended",
    )
    assert req.state == LeaveState.PENDING_ROUTING

    # 4. Establishment routes
    req = routing.route_leave_request(
        request_id=req.id,
        actor_user_id=300,
        actor_role="Establishment",
        remark="Verified entitlement",
    )
    assert req.state == LeaveState.PENDING_SANCTION

    # 5. Dean sanctions
    req = sanction.sanction_leave_request(
        request_id=req.id,
        actor_user_id=400,
        actor_role="Dean",
        approve=True,
        remark="Sanctioned",
    )
    assert req.state == LeaveState.APPROVED

    # Check EL balance: 30 - 5 = 25
    bal = get_user_balance(user_id, 2026, "EL")
    assert bal == Decimal("25.0")


def test_withdraw_leave_request(leave_setup):
    user_id = 100
    starts = datetime.date(2026, 3, 2)
    ends = datetime.date(2026, 3, 3)

    req = apply.submit_leave_request(
        user_id=user_id,
        category="CL",
        starts_on=starts,
        ends_on=ends,
        reason="Personal work",
    )
    assert req.state == LeaveState.PENDING_REVIEW

    withdrawn_req = withdraw.withdraw_leave_request(
        request_id=req.id,
        user_id=user_id,
        remark="No longer needed",
    )
    assert withdrawn_req.state == LeaveState.WITHDRAWN

    # Balance remains untouched at 8.0
    bal = get_user_balance(user_id, 2026, "CL")
    assert bal == Decimal("8.0")


def test_cancel_approved_leave_restores_balance(leave_setup):
    user_id = 100
    # Date strictly in future relative to today
    today = datetime.date.today()
    future_start = today + datetime.timedelta(days=10)
    future_end = today + datetime.timedelta(days=11)

    req = apply.submit_leave_request(
        user_id=user_id,
        category="CL",
        starts_on=future_start,
        ends_on=future_end,
        reason="Planned trip",
    )
    review.review_leave_request(
        request_id=req.id,
        reviewer_user_id=999,
        reviewer_role="Unit Head",
        approve=True,
    )
    assert get_user_balance(user_id, future_start.year, "CL") == Decimal("6.0")

    # Request cancellation
    c_req = cancel.request_cancellation(
        request_id=req.id,
        user_id=user_id,
        remark="Trip cancelled",
    )
    assert c_req.state == LeaveState.CANCELLATION_PENDING_REVIEW

    # Unit head approves cancellation
    decided_c_req = review.review_leave_request(
        request_id=req.id,
        reviewer_user_id=999,
        reviewer_role="Unit Head",
        approve=True,
        remark="Cancellation approved",
    )
    assert decided_c_req.state == LeaveState.CANCELLED

    # Balance restored back to 8.0
    assert get_user_balance(user_id, future_start.year, "CL") == Decimal("8.0")


def test_resumption_early_return_restores_unused_balance(leave_setup):
    user_id = 100
    starts = datetime.date(2026, 1, 5) # Mon
    ends = datetime.date(2026, 1, 9)   # Fri (5 days)

    req = apply.submit_leave_request(
        user_id=user_id,
        category="EL",
        starts_on=starts,
        ends_on=ends,
        reason="Conference",
    )
    # Complete full approval hierarchy to trigger ledger debit
    req = review.review_leave_request(req.id, reviewer_user_id=200, reviewer_role="Unit Head", approve=True)
    req = routing.route_leave_request(req.id, actor_user_id=300, actor_role="Establishment")
    req = sanction.sanction_leave_request(req.id, actor_user_id=400, actor_role="Dean", approve=True)
    assert req.state == LeaveState.APPROVED
    assert get_user_balance(user_id, 2026, "EL") == Decimal("25.0")

    # Employee returns early on Wednesday 2026-01-07
    resumed_date = datetime.date(2026, 1, 7)
    res_req = resumption.submit_resumption(
        request_id=req.id,
        user_id=user_id,
        resumed_on=resumed_date,
        remark="Conference ended early",
    )
    assert res_req.state == LeaveState.RESUMPTION_PENDING

    # Verifier verifies resumption
    closed_req = resumption.verify_resumption(
        request_id=req.id,
        verifier_user_id=999,
        verifier_role="Authority",
        remark="Verified attendance",
    )
    assert closed_req.state == LeaveState.CLOSED

    # Originally debited 5 days. Resumed on Jan 7 -> actual end Jan 6 (2 days).
    # 3 days should be restored to balance: 25 + 3 = 28
    bal = get_user_balance(user_id, 2026, "EL")
    assert bal == Decimal("28.0")


def test_year_end_processing(leave_setup):
    user_id = 100
    year = 2026

    # Run year-end processing for faculty user 100
    summary = yearend.run_year_end_processing(
        year=year,
        user_ids=[user_id],
        faculty_user_ids=[user_id],
    )
    assert summary["users_processed"] == 1
    assert summary["entries_created"] > 0

    # User had 60 VL -> converted to 30 EL in 2027
    el_next_year = get_user_balance(user_id, year + 1, "EL")
    # Converted EL (30.0) + carried forward EL (30.0) = 60.0
    assert el_next_year == Decimal("60.0")


def test_sla_clocks_processing(leave_setup):
    policy = leave_setup["policy"]
    SlaRule.objects.create(
        policy=policy,
        state=LeaveState.PENDING_REVIEW,
        remind_after_hours=24,
        escalate_after_hours=48,
        escalate_to_designation="Director",
    )

    req = LeaveRequest.objects.create(
        user_id=100,
        category="CL",
        starts_on=datetime.date(2026, 1, 5),
        ends_on=datetime.date(2026, 1, 6),
        requested_days=Decimal("2.0"),
        reason="Testing SLA",
        state=LeaveState.PENDING_REVIEW,
    )
    clock = SlaClock.objects.create(
        request=req,
        state=LeaveState.PENDING_REVIEW,
    )

    # Fast forward clock entered_at to 50 hours ago
    past_time = datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=50)
    SlaClock.objects.filter(pk=clock.pk).update(entered_at=past_time)

    res = sla.process_sla_clocks()
    assert res["escalated"] == 1
