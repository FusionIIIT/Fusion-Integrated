"""Rebates — MMS-UC-014, 015. BR-MMS-019, 021..025. BW-MMS-05/06/07, CW-MMS-03."""
import pytest

from core.api.exceptions import BadRequestError, ConflictError, PermissionDeniedError
from modules.mms.domain.state_machine import RuleViolation
from modules.mms.models import MessRebate
from modules.mms.services import operations as svc
from modules.mms.tests.factories import RebateFactory
from modules.mms.tests.helpers import (
    CARETAKER_ID,
    OTHER_STUDENT_ID,
    STUDENT_ID,
    admin,
    caretaker,
    student,
    warden,
)
from modules.mms.tests.helpers import (
    days_from_today as day,
)

pytestmark = pytest.mark.django_db


def _submit(start=5, end=8, who=None, reason="medical"):
    return svc.submit_rebate_request(actor=who or student(), start_date=day(start),
                                     end_date=day(end), reason=reason)


# ---- submission ---------------------------------------------------------------
def test_student_submits_a_rebate(sent):
    r = _submit(5, 8)
    assert (r.status, r.user_id, r.duration_days) == ("submitted", STUDENT_ID, 4)
    assert (r.original_start_date, r.original_end_date) == (day(5), day(8))
    assert r.modified_by_caretaker is False
    [n] = sent("rebate_submitted")
    assert n.recipient_user_id == STUDENT_ID


def test_br021_exactly_three_days_is_accepted():
    assert _submit(5, 7).duration_days == 3


@pytest.mark.parametrize("end", [5, 6])
def test_br021_one_or_two_days_is_refused(end, sent):
    with pytest.raises(RuleViolation) as e:
        _submit(5, end)
    assert e.value.rule_id == "BR-MMS-021"
    assert MessRebate.objects.count() == 0
    assert sent() == []


def test_br022_exactly_one_day_of_lead_time_is_accepted():
    assert _submit(1, 4).status == "submitted"


@pytest.mark.parametrize("start", [0, -1, -10])
def test_br022_same_day_or_backdated_is_refused(start):
    with pytest.raises(RuleViolation) as e:
        _submit(start, start + 5)
    assert e.value.rule_id == "BR-MMS-022"


def test_submission_date_can_be_injected():
    """The service takes `submission_date` so schedulers and tests need not fake the clock."""
    r = svc.submit_rebate_request(actor=student(), start_date=day(20), end_date=day(25),
                                  reason="family function", submission_date=day(19))
    assert r.status == "submitted"
    with pytest.raises(RuleViolation):
        svc.submit_rebate_request(actor=student(), start_date=day(20), end_date=day(25),
                                  reason="x", submission_date=day(20))


@pytest.mark.parametrize("status", ["submitted", "approved"])
@pytest.mark.parametrize(("start", "end"), [
    (5, 8),      # identical
    (7, 10),     # overlaps the tail
    (2, 5),      # overlaps the head
])
def test_br023_overlap_with_a_live_rebate_is_refused(status, start, end):
    RebateFactory(status=status, start_date=day(4), end_date=day(10), duration_days=7)
    with pytest.raises(RuleViolation) as e:
        _submit(start, end)
    assert e.value.rule_id == "BR-MMS-023"


def test_br023_nested_inside_existing():
    RebateFactory(start_date=day(4), end_date=day(14), duration_days=11)
    with pytest.raises(RuleViolation) as e:
        _submit(6, 8)
    assert e.value.rule_id == "BR-MMS-023"


def test_br023_enclosing_an_existing_rebate_is_refused():
    RebateFactory(start_date=day(6), end_date=day(8), duration_days=3)
    with pytest.raises(RuleViolation):
        _submit(3, 12)


def test_br023_touching_a_single_shared_day_is_an_overlap():
    RebateFactory(start_date=day(5), end_date=day(7), duration_days=3)
    with pytest.raises(RuleViolation):
        _submit(7, 9)


def test_br023_back_to_back_rebates_do_not_overlap():
    RebateFactory(start_date=day(5), end_date=day(7), duration_days=3)
    assert _submit(8, 10).status == "submitted"


def test_br023_a_rejected_rebate_does_not_block_the_same_dates():
    RebateFactory(rejected=True)
    assert _submit(5, 8).status == "submitted"


def test_br023_another_students_rebate_does_not_block():
    RebateFactory(user_id=OTHER_STUDENT_ID)
    assert _submit(5, 8).user_id == STUDENT_ID


@pytest.mark.parametrize("who", [caretaker, warden, admin])
def test_only_students_submit_rebates(who):
    with pytest.raises(PermissionDeniedError):
        _submit(who=who())


# ---- review: BW-MMS-05 / 06 / 07 ----------------------------------------------
def test_bw05_approve_as_submitted(sent):
    r = RebateFactory()
    out = svc.review_rebate_request(actor=caretaker(), rebate_id=r.pk, action="approve")
    assert out.status == "approved"
    assert (out.start_date, out.end_date, out.duration_days) == (day(5), day(8), 4)
    assert out.modified_by_caretaker is False
    assert (out.reviewed_by_user_id, out.reviewed_at is not None) == (CARETAKER_ID, True)
    assert len(sent("rebate_approved")) == 1


def test_bw06_dates_modified_then_approved_and_billing_dates_follow():
    r = RebateFactory(original_start_date=day(5), original_end_date=day(8))
    out = svc.review_rebate_request(actor=caretaker(), rebate_id=r.pk, action="approve",
                                    modified_start_date=day(6), modified_end_date=day(12))
    assert (out.start_date, out.end_date, out.duration_days) == (day(6), day(12), 7)
    assert out.modified_by_caretaker is True
    assert (out.original_start_date, out.original_end_date) == (day(5), day(8))   # audit trail


def test_bw06_modifying_only_the_end_date_keeps_the_start():
    r = RebateFactory()
    out = svc.review_rebate_request(actor=caretaker(), rebate_id=r.pk, action="approve",
                                    modified_end_date=day(10))
    assert (out.start_date, out.end_date, out.duration_days) == (day(5), day(10), 6)


def test_bw06_modifying_only_the_start_date_keeps_the_end():
    r = RebateFactory()
    out = svc.review_rebate_request(actor=caretaker(), rebate_id=r.pk, action="approve",
                                    modified_start_date=day(4))
    assert (out.start_date, out.end_date, out.duration_days) == (day(4), day(8), 5)


def test_bw06_modified_dates_still_obey_the_three_day_minimum():
    r = RebateFactory()
    with pytest.raises(RuleViolation) as e:
        svc.review_rebate_request(actor=caretaker(), rebate_id=r.pk, action="approve",
                                  modified_start_date=day(5), modified_end_date=day(6))
    assert e.value.rule_id == "BR-MMS-021"
    r.refresh_from_db()
    assert (r.status, r.duration_days, r.modified_by_caretaker) == ("submitted", 4, False)


def test_bw07_reject(sent):
    r = RebateFactory()
    out = svc.review_rebate_request(actor=caretaker(), rebate_id=r.pk, action="reject",
                                    remarks="peak week")
    assert (out.status, out.remarks) == ("rejected", "peak week")
    assert len(sent("rebate_rejected")) == 1


def test_a_rejection_ignores_any_date_modification():
    r = RebateFactory()
    out = svc.review_rebate_request(actor=caretaker(), rebate_id=r.pk, action="reject",
                                    modified_start_date=day(1), modified_end_date=day(30))
    assert (out.start_date, out.end_date, out.modified_by_caretaker) == (day(5), day(8), False)


@pytest.mark.parametrize("decided", ["approved", "rejected"])
def test_a_decided_rebate_cannot_be_decided_again(decided):
    r = RebateFactory(status=decided)
    with pytest.raises(ConflictError):
        svc.review_rebate_request(actor=caretaker(), rebate_id=r.pk, action="approve")


@pytest.mark.parametrize("who", [warden, student, admin])
def test_only_the_caretaker_decides_rebates(who):
    r = RebateFactory()
    with pytest.raises(PermissionDeniedError):
        svc.review_rebate_request(actor=who(), rebate_id=r.pk, action="approve")
    r.refresh_from_db()
    assert r.status == "submitted"


def test_an_unknown_rebate_action_changes_nothing():
    r = RebateFactory()
    with pytest.raises(BadRequestError):
        svc.review_rebate_request(actor=caretaker(), rebate_id=r.pk, action="approved")
    r.refresh_from_db()
    assert r.status == "submitted"
