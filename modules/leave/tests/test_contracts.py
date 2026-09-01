"""What other modules are told about an absence.

get_absences recognised only the settled states, so a request under
cancellation or extension review disappeared from the answer while its approval
was still in force. A scheduling consumer would have assigned somebody whose
leave had not been cancelled, or who had already gone.
"""
from datetime import date

import pytest

from modules.leave import contracts
from modules.leave.domain.categories import Category
from modules.leave.domain.state_machine import State
from modules.leave.models import LeaveRequest
from modules.leave.tests.factories import YEAR

pytestmark = pytest.mark.django_db
U, OTHER = 701, 702

START, END = date(YEAR, 3, 2), date(YEAR, 3, 6)
DURING = date(YEAR, 3, 4)


def request_in(state: State, user_id: int = U) -> LeaveRequest:
    return LeaveRequest.objects.create(
        user_id=user_id, category=Category.EL.value, state=state.value,
        starts_on=START, ends_on=END, reason="x", requested_days=5, unit="CSE")


class TestWhoCountsAsAway:
    @pytest.mark.parametrize("state", [
        State.APPROVED_NOT_STARTED,
        State.ONGOING,
        State.AWAITING_RESUMPTION,
        State.AWAITING_RESUMPTION_VERIFICATION,
    ])
    def test_the_settled_states_count(self, state):
        request_in(state)

        assert U in contracts.get_absences([U], DURING)

    @pytest.mark.parametrize("state", [
        State.CANCELLATION_UNIT_HEAD,
        State.CANCELLATION_ESTABLISHMENT,
        State.CANCELLATION_FINAL,
    ])
    def test_a_cancellation_under_review_still_counts(self, state):
        request_in(state)

        # Asking to cancel does not undo the approval; they are still going.
        assert U in contracts.get_absences([U], DURING)

    @pytest.mark.parametrize("state", [
        State.EXTENSION_AWAITING_SUBSTITUTE,
        State.EXTENSION_APPLICANT_ACTION_REQUIRED,
        State.EXTENSION_AWAITING_UNIT_HEAD,
        State.EXTENSION_AWAITING_ESTABLISHMENT,
        State.EXTENSION_AWAITING_FINAL,
    ])
    def test_an_extension_under_review_still_counts(self, state):
        request_in(state)

        # The original leave is running regardless of the extension's fate.
        assert U in contracts.get_absences([U], DURING)

    @pytest.mark.parametrize("state", [
        State.DRAFT,
        State.AWAITING_UNIT_HEAD,
        State.AWAITING_FINAL_SANCTION,
        State.REJECTED,
        State.WITHDRAWN,
        State.CANCELLED,
        State.CLOSED,
    ])
    def test_nothing_unapproved_or_finished_counts(self, state):
        request_in(state)

        assert contracts.get_absences([U], DURING) == {}


class TestTheAnswerShape:
    def test_a_reviewed_absence_says_so(self):
        request_in(State.CANCELLATION_UNIT_HEAD)

        assert contracts.get_absences([U], DURING)[U].under_review is True

    def test_a_settled_absence_does_not(self):
        request_in(State.ONGOING)

        assert contracts.get_absences([U], DURING)[U].under_review is False

    def test_dates_outside_the_leave_are_not_covered(self):
        request_in(State.ONGOING)

        assert contracts.get_absences([U], date(YEAR, 3, 20)) == {}

    def test_it_answers_for_everybody_in_one_call(self):
        request_in(State.ONGOING, user_id=U)
        request_in(State.CANCELLATION_FINAL, user_id=OTHER)

        answer = contracts.get_absences([U, OTHER, 999], DURING)

        assert sorted(answer) == [U, OTHER]

    def test_an_empty_list_costs_nothing(self, django_assert_num_queries):
        with django_assert_num_queries(0):
            assert contracts.get_absences([], DURING) == {}
