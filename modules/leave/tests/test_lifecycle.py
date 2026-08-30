"""Cancellation, extension and resumption, and what each returns to the balance."""
from datetime import date
from decimal import Decimal

import pytest

from core.api.exceptions import BadRequestError, ConflictError
from modules.leave.domain.categories import Category
from modules.leave.domain.state_machine import State
from modules.leave.models import EntryReason
from modules.leave.selectors import balances
from modules.leave.services import decisions, lifecycle
from modules.leave.services import requests as service
from modules.leave.tests.factories import setup_all

pytestmark = pytest.mark.django_db

USER, HEAD, ESTT, AUTH = 501, 601, 602, 603
D = Decimal

# Mon 10 Aug to Mon 17 Aug 2026: eight continuous days, 15 Aug a closed holiday.
START, END = date(2026, 8, 10), date(2026, 8, 17)


@pytest.fixture
def configured():
    return setup_all(USER)


def approved_el():
    r = service.submit(
        user_id=USER, category=Category.EL, starts_on=START, ends_on=END,
        reason="travel", faculty=False,
    )
    r = decisions.unit_head_decides(request=r, actor_user_id=HEAD, approve=True)
    r = decisions.establishment_routes(request=r, actor_user_id=ESTT)
    return decisions.sanction(request=r, actor_user_id=AUTH, approve=True)


class TestCancellation:
    """BR-EL-023. Before the leave begins, and the whole charge comes back."""

    def test_the_full_charge_is_returned(self, configured):
        r = approved_el()
        assert balances.available(USER, 2026, Category.EL) == D(22)
        r = lifecycle.request_cancellation(request=r, actor_user_id=USER)
        r = lifecycle.decide_cancellation_unit_head(request=r, actor_user_id=HEAD, approve=True)
        r = lifecycle.route_cancellation(request=r, actor_user_id=ESTT)
        r = lifecycle.decide_cancellation_final(request=r, actor_user_id=AUTH, approve=True)
        assert r.state == State.CANCELLED.value
        assert balances.available(USER, 2026, Category.EL) == D(30)

    def test_a_refused_cancellation_leaves_the_leave_standing(self, configured):
        r = approved_el()
        r = lifecycle.request_cancellation(request=r, actor_user_id=USER)
        r = lifecycle.decide_cancellation_unit_head(request=r, actor_user_id=HEAD, approve=False)
        assert r.state == State.APPROVED_NOT_STARTED.value
        assert balances.available(USER, 2026, Category.EL) == D(22)

    def test_the_return_is_its_own_ledger_row(self, configured):
        r = approved_el()
        r = lifecycle.request_cancellation(request=r, actor_user_id=USER)
        r = lifecycle.decide_cancellation_unit_head(request=r, actor_user_id=HEAD, approve=True)
        r = lifecycle.route_cancellation(request=r, actor_user_id=ESTT)
        lifecycle.decide_cancellation_final(request=r, actor_user_id=AUTH, approve=True)
        reasons = [e.reason for e in balances.statement(USER, 2026, Category.EL)]
        assert EntryReason.CONSUMED in reasons and EntryReason.CANCELLED in reasons

    def test_only_the_applicant_may_ask(self, configured):
        with pytest.raises(ConflictError):
            lifecycle.request_cancellation(request=approved_el(), actor_user_id=HEAD)


class TestExtension:
    """BR-EL-025. Only the additional days are charged."""

    def test_only_the_increment_is_charged(self, configured):
        r = lifecycle.begin(request=approved_el())
        r = lifecycle.request_extension(
            request=r, actor_user_id=USER, new_end=date(2026, 8, 20)
        )
        r = lifecycle.recommend_extension(request=r, actor_user_id=HEAD)
        r = lifecycle.route_extension(request=r, actor_user_id=ESTT)
        r = lifecycle.decide_extension(
            request=r, actor_user_id=AUTH, approve=True, new_end=date(2026, 8, 20)
        )
        # Eight days already charged, three more to the 20th.
        assert balances.available(USER, 2026, Category.EL) == D(19)
        assert r.requested_days == D(11)
        assert r.state == State.ONGOING.value

    def test_a_refused_extension_leaves_the_leave_running_unchanged(self, configured):
        r = lifecycle.begin(request=approved_el())
        r = lifecycle.request_extension(
            request=r, actor_user_id=USER, new_end=date(2026, 8, 20)
        )
        r = lifecycle.recommend_extension(request=r, actor_user_id=HEAD)
        r = lifecycle.route_extension(request=r, actor_user_id=ESTT)
        r = lifecycle.decide_extension(request=r, actor_user_id=AUTH, approve=False)
        assert r.state == State.ONGOING.value
        assert balances.available(USER, 2026, Category.EL) == D(22)

    def test_casual_leave_cannot_be_extended(self, configured):
        r = service.submit(
            user_id=USER, category=Category.CL, starts_on=date(2026, 9, 1),
            ends_on=date(2026, 9, 1), reason="x", faculty=False,
        )
        r = decisions.unit_head_decides(request=r, actor_user_id=HEAD, approve=True)
        r = lifecycle.begin(request=r)
        with pytest.raises(BadRequestError) as exc:
            lifecycle.request_extension(
                request=r, actor_user_id=USER, new_end=date(2026, 9, 3)
            )
        assert exc.value.code == "not_extendable"

    def test_an_extension_must_actually_extend(self, configured):
        r = lifecycle.begin(request=approved_el())
        with pytest.raises(BadRequestError) as exc:
            lifecycle.request_extension(request=r, actor_user_id=USER, new_end=END)
        assert exc.value.code == "extension_not_longer"


class TestResumption:
    """BR-EL-027, BR-EL-028."""

    def test_finishing_on_time_returns_nothing(self, configured):
        r = lifecycle.begin(request=approved_el())
        r = lifecycle.await_resumption(request=r)
        r = lifecycle.submit_resumption(
            request=r, actor_user_id=USER, resumed_on=date(2026, 8, 18)
        )
        r = lifecycle.verify_resumption(request=r, actor_user_id=ESTT)
        assert r.state == State.CLOSED.value
        assert balances.available(USER, 2026, Category.EL) == D(22)
        assert r.actual_days == D(8)

    def test_coming_back_early_returns_the_unused_days(self, configured):
        r = lifecycle.begin(request=approved_el())
        # Back on Monday the 17th; the default trims the closed weekend.
        r = lifecycle.submit_resumption(request=r, actor_user_id=USER, resumed_on=END)
        r = lifecycle.verify_resumption(request=r, actor_user_id=ESTT)
        assert r.actual_days == D(5)
        # Thirty credited less the five actually taken.
        assert balances.available(USER, 2026, Category.EL) == D(25)

    def test_nothing_is_returned_before_verification(self, configured):
        # SRS-EL-086. Reporting a return is not the same as it being verified.
        r = lifecycle.begin(request=approved_el())
        lifecycle.submit_resumption(request=r, actor_user_id=USER, resumed_on=END)
        assert balances.available(USER, 2026, Category.EL) == D(22)

    def test_verification_may_ask_for_more_first(self, configured):
        r = lifecycle.begin(request=approved_el())
        r = lifecycle.submit_resumption(request=r, actor_user_id=USER, resumed_on=END)
        r = lifecycle.query_resumption(
            request=r, actor_user_id=ESTT, remark="attach the joining report"
        )
        assert r.state == State.AWAITING_RESUMPTION_VERIFICATION.value
        assert balances.available(USER, 2026, Category.EL) == D(22)
        r = lifecycle.verify_resumption(request=r, actor_user_id=ESTT)
        assert r.state == State.CLOSED.value

    def test_the_restoration_names_the_policy_that_decided_it(self, configured):
        r = lifecycle.begin(request=approved_el())
        r = lifecycle.submit_resumption(request=r, actor_user_id=USER, resumed_on=END)
        lifecycle.verify_resumption(request=r, actor_user_id=ESTT)
        restored = [
            e
            for e in balances.statement(USER, 2026, Category.EL)
            if e.reason == EntryReason.RESTORED
        ]
        assert len(restored) == 1
        assert restored[0].days == D(3)
        assert "trim" in restored[0].note
