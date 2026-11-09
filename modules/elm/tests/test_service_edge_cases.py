from datetime import date
from decimal import Decimal

import pytest

from core.api.exceptions import ConflictError, DomainError, NotFoundError
from modules.elm.models import LeaveBalance, LeaveRequest, SubstituteAssignment
from modules.elm.services.leave import (
    apply_for_leave,
    cancel_approved_leave,
    extend_leave,
    record_offline_sanctioned_leave,
    respond_substitute,
    review_leave_request,
    review_resumption,
    submit_resumption_of_duty,
    withdraw_leave_request,
)

pytestmark = pytest.mark.django_db


def _balance(*, user=101, category="CL", year=2026, credited="8", availed="0", balance="8"):
    return LeaveBalance.objects.create(user_id=user, category=category, year=year,
                                       credited=Decimal(credited), availed=Decimal(availed),
                                       balance=Decimal(balance))


def _leave(*, user=101, category="CL", start=date(2026, 11, 2), end=date(2026, 11, 2),
           days="1", status="under_review", **kwargs):
    return LeaveRequest.objects.create(user_id=user, category=category, start_date=start,
                                       end_date=end, leave_days=Decimal(days), purpose="Test",
                                       status=status, **kwargs)


@pytest.mark.parametrize("destination,contact", [("", "123"), ("Bhopal", ""), ("  ", "123"), ("Bhopal", "   ")])
def test_station_leave_requires_destination_and_contact(applicant_balance, destination, contact):
    with pytest.raises(DomainError, match="Station leave requires"):
        apply_for_leave(user_id=101, category="CL", start_date=date(2026, 11, 2),
                        end_date=date(2026, 11, 2), purpose="Trip", is_station_leave=True,
                        destination=destination, emergency_contact=contact)


def test_non_station_leave_does_not_require_destination(applicant_balance):
    req = apply_for_leave(user_id=101, category="CL", start_date=date(2026, 11, 2),
                          end_date=date(2026, 11, 2), purpose="Personal")
    assert not req.is_station_leave


@pytest.fixture
def applicant_balance(db):
    return _balance()


def test_applicant_cannot_nominate_self(applicant_balance):
    with pytest.raises(DomainError, match="cannot nominate themselves"):
        apply_for_leave(user_id=101, category="CL", start_date=date(2026, 11, 2),
                        end_date=date(2026, 11, 2), purpose="Personal", substitute_id=101)


@pytest.mark.parametrize("category", ["CL", "RH", "SCL", "EL", "VL", "COL"])
def test_missing_balance_is_not_treated_as_zero_or_unlimited(category):
    with pytest.raises(NotFoundError, match="No leave balance"):
        apply_for_leave(user_id=101, category=category, start_date=date(2026, 11, 2),
                        end_date=date(2026, 11, 2), purpose="Personal")


def test_application_with_exact_available_balance_succeeds():
    _balance(balance="1")
    req = apply_for_leave(user_id=101, category="CL", start_date=date(2026, 11, 2),
                          end_date=date(2026, 11, 2), purpose="Personal")
    assert req.leave_days == Decimal("1")


def test_application_over_balance_is_rejected_and_creates_nothing():
    _balance(balance="0.5")
    with pytest.raises(DomainError, match="Insufficient balance"):
        apply_for_leave(user_id=101, category="CL", start_date=date(2026, 11, 2),
                        end_date=date(2026, 11, 2), purpose="Personal")
    assert not LeaveRequest.objects.exists()


@pytest.mark.parametrize("status", ["withdrawn", "rejected", "cancelled"])
def test_terminal_nonactive_requests_do_not_block_new_application(status):
    _balance()
    _leave(status=status)
    req = apply_for_leave(user_id=101, category="CL", start_date=date(2026, 11, 2),
                          end_date=date(2026, 11, 2), purpose="New request")
    assert req.status == "under_review"


def test_opposite_half_day_requests_on_same_date_are_allowed():
    _balance()
    _leave(start=date(2026, 11, 2), end=date(2026, 11, 2), days="0.5", half_day="first")
    req = apply_for_leave(user_id=101, category="CL", start_date=date(2026, 11, 2),
                          end_date=date(2026, 11, 2), half_day="second", purpose="Other half")
    assert req.leave_days == Decimal("0.5")


def test_same_half_day_overlap_is_rejected():
    _balance()
    _leave(days="0.5", half_day="first")
    with pytest.raises(ConflictError):
        apply_for_leave(user_id=101, category="CL", start_date=date(2026, 11, 2),
                        end_date=date(2026, 11, 2), half_day="first", purpose="Duplicate")


def test_successful_application_writes_initial_audit_event_and_assignment():
    _balance()
    req = apply_for_leave(user_id=101, category="CL", start_date=date(2026, 11, 2),
                          end_date=date(2026, 11, 2), purpose="Coverage", substitute_id=102)
    assert list(req.actions.values_list("actor_id", "action")) == [(101, "submitted")]
    assignment = SubstituteAssignment.objects.get(leave_request=req)
    assert (assignment.substitute_id, assignment.status) == (102, "pending")


@pytest.mark.parametrize("action", ["accept", "decline"])
def test_substitute_response_updates_assignment_time_remarks_and_audit(action):
    _balance()
    req = apply_for_leave(user_id=101, category="CL", start_date=date(2026, 11, 2),
                          end_date=date(2026, 11, 2), purpose="Coverage", substitute_id=102)
    assignment = respond_substitute(substitute_id=102, request_id=req.pk, action=action, remarks="Noted")
    assert assignment.responded_at is not None
    assert assignment.remarks == "Noted"
    assert req.actions.filter(actor_id=102, action=f"substitute_{action}ed", comments="Noted").exists()


@pytest.mark.parametrize("action", ["accept", "decline"])
def test_non_assigned_or_already_responded_substitute_is_rejected(action):
    _balance()
    req = apply_for_leave(user_id=101, category="CL", start_date=date(2026, 11, 2),
                          end_date=date(2026, 11, 2), purpose="Coverage", substitute_id=102)
    with pytest.raises(NotFoundError):
        respond_substitute(substitute_id=999, request_id=req.pk, action=action)
    respond_substitute(substitute_id=102, request_id=req.pk, action=action)
    with pytest.raises(NotFoundError):
        respond_substitute(substitute_id=102, request_id=req.pk, action=action)


def test_invalid_substitute_action_is_rejected():
    with pytest.raises(DomainError, match="Action must"):
        respond_substitute(substitute_id=102, request_id=1, action="maybe")


def test_recommendation_and_rejection_record_reason_and_history():
    for action, status in (("recommend", "recommended"), ("reject", "rejected")):
        req = _leave(start=date(2026, 11, 4), end=date(2026, 11, 4))
        changed = review_leave_request(reviewer_id=200, request_id=req.pk, action=action, reason="Reviewed")
        assert changed.status == status
        assert changed.actions.filter(actor_id=200, action=action, comments="Reviewed").exists()
        if action == "reject":
            assert changed.rejection_reason == "Reviewed"


def test_review_nonexistent_request_is_not_found():
    with pytest.raises(NotFoundError):
        review_leave_request(reviewer_id=200, request_id=99999, action="approve")


@pytest.mark.parametrize("action", ["invalid", "withdraw", "sanction"])
def test_invalid_review_action_is_rejected(action):
    req = _leave()
    with pytest.raises(DomainError):
        review_leave_request(reviewer_id=200, request_id=req.pk, action=action)


@pytest.mark.parametrize("status", ["sanctioned", "rejected", "withdrawn", "cancelled"])
def test_only_pending_review_states_can_be_withdrawn(status):
    req = _leave(status=status)
    with pytest.raises(DomainError, match="Cannot withdraw"):
        withdraw_leave_request(user_id=101, request_id=req.pk)


def test_withdrawal_does_not_allow_other_users_to_withdraw():
    req = _leave()
    with pytest.raises(NotFoundError):
        withdraw_leave_request(user_id=202, request_id=req.pk)


@pytest.mark.parametrize("status", ["submitted", "awaiting_substitute", "under_review", "recommended"])
def test_pending_statuses_can_be_withdrawn(status):
    req = _leave(status=status)
    result = withdraw_leave_request(user_id=101, request_id=req.pk)
    assert result.status == "withdrawn"
    assert result.actions.filter(action="withdrawn").exists()


def test_cannot_cancel_on_or_after_start_date():
    _balance(availed="1", balance="7")
    req = _leave(status="sanctioned")
    for today in (req.start_date, date(2026, 12, 1)):
        with pytest.raises(DomainError, match="already started"):
            cancel_approved_leave(user_id=101, request_id=req.pk, today_date=today)


def test_cannot_cancel_another_users_or_missing_request():
    req = _leave(status="sanctioned")
    for user, pk in ((202, req.pk), (101, 99999)):
        with pytest.raises(NotFoundError):
            cancel_approved_leave(user_id=user, request_id=pk, today_date=date(2026, 10, 1))


@pytest.mark.parametrize("category", ["CL", "RH", "SCL"])
def test_only_continuous_leave_categories_can_be_extended(category):
    req = _leave(category=category, status="sanctioned")
    with pytest.raises(DomainError, match="only permitted"):
        extend_leave(user_id=101, request_id=req.pk, new_end_date=date(2026, 11, 4))


@pytest.mark.parametrize("status", ["under_review", "rejected", "withdrawn", "cancelled"])
def test_only_sanctioned_leave_can_be_extended(status):
    req = _leave(category="EL", status=status)
    with pytest.raises(DomainError, match="Only sanctioned"):
        extend_leave(user_id=101, request_id=req.pk, new_end_date=date(2026, 11, 4))


@pytest.mark.parametrize("new_end", [date(2026, 11, 2), date(2026, 11, 1)])
def test_extension_must_end_after_existing_end(new_end):
    req = _leave(category="EL", status="sanctioned")
    with pytest.raises(DomainError, match="must be after"):
        extend_leave(user_id=101, request_id=req.pk, new_end_date=new_end)


def test_extension_insufficient_balance_rolls_back_without_mutation():
    _balance(category="EL", credited="10", availed="10", balance="0")
    req = _leave(category="EL", status="sanctioned")
    with pytest.raises(DomainError, match="Insufficient balance"):
        extend_leave(user_id=101, request_id=req.pk, new_end_date=date(2026, 11, 4))
    req.refresh_from_db()
    assert req.end_date == date(2026, 11, 2)
    assert req.leave_days == Decimal("1")


def test_resumption_requires_sanctioned_owned_request():
    req = _leave(status="under_review")
    with pytest.raises(DomainError, match="only be submitted for sanctioned"):
        submit_resumption_of_duty(user_id=101, request_id=req.pk, actual_resumption_date=date(2026, 11, 3))
    with pytest.raises(NotFoundError):
        submit_resumption_of_duty(user_id=202, request_id=req.pk, actual_resumption_date=date(2026, 11, 3))


def test_resumption_review_requires_pending_resumption():
    req = _leave(status="sanctioned")
    with pytest.raises(NotFoundError):
        review_resumption(reviewer_id=200, request_id=req.pk)


def test_resumption_same_as_expected_date_keeps_balances_unchanged():
    _balance(category="EL", credited="30", availed="5", balance="25")
    req = _leave(category="EL", status="sanctioned", start=date(2026, 11, 1),
                 end=date(2026, 11, 5), days="5")
    submit_resumption_of_duty(user_id=101, request_id=req.pk, actual_resumption_date=date(2026, 11, 6))
    reviewed = review_resumption(reviewer_id=200, request_id=req.pk)
    bal = LeaveBalance.objects.get(user_id=101, category="EL")
    assert reviewed.resumption_status == "completed"
    assert (reviewed.end_date, reviewed.leave_days) == (date(2026, 11, 5), Decimal("5"))
    assert (bal.balance, bal.availed) == (Decimal("25"), Decimal("5"))


def test_offline_leave_requires_existing_balance():
    with pytest.raises(NotFoundError):
        record_offline_sanctioned_leave(admin_id=9, user_id=101, category="CL",
                                        start_date=date(2026, 11, 2), end_date=date(2026, 11, 2),
                                        purpose="Offline", sanction_reference="OFF/1")


def test_offline_record_is_audited_and_records_reference():
    _balance()
    req = record_offline_sanctioned_leave(admin_id=9, user_id=101, category="CL",
                                          start_date=date(2026, 11, 2), end_date=date(2026, 11, 2),
                                          purpose="Offline", sanction_reference="OFF/1")
    assert req.is_offline_recorded and req.offline_reference == "OFF/1"
    assert req.actions.filter(actor_id=9, action="offline_recorded").exists()


def test_offline_leave_cannot_make_balance_negative():
    _balance(balance="0")
    with pytest.raises(DomainError, match="Insufficient balance"):
        record_offline_sanctioned_leave(admin_id=9, user_id=101, category="CL",
                                        start_date=date(2026, 11, 2), end_date=date(2026, 11, 2),
                                        purpose="Offline", sanction_reference="OFF/1")
