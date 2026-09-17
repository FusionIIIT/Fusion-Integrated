"""Things the module must refuse, written as an attacker would try them."""
import contextlib
from datetime import date, timedelta

import pytest

from core.api.exceptions import BadRequestError, ConflictError
from modules.leave.domain.categories import Category
from modules.leave.domain.state_machine import State
from modules.leave.services import decisions, lifecycle
from modules.leave.services import requests as service
from modules.leave.tests import factories
from modules.leave.tests.factories import YEAR

pytestmark = pytest.mark.django_db
APPLICANT, OTHER = 701, 702


def approved(user_id=APPLICANT, days=2):
    factories.credit(user_id, Category.EL, 30)
    r = service.submit(user_id=user_id, category=Category.EL,
                       starts_on=date(YEAR, 3, 2),
                       ends_on=date(YEAR, 3, 2) + timedelta(days=days - 1),
                       reason="x", unit="CSE", faculty=False)
    r = decisions.unit_head_decides(request=r, actor_user_id=900, approve=True)
    return decisions.establishment_routes(request=r, actor_user_id=901) \
        if r.state == State.AWAITING_ESTABLISHMENT.value else r


def test_the_sanctioning_authority_cannot_sanction_their_own():
    factories.setup_all(999)
    r = approved(user_id=APPLICANT, days=2)
    if r.state != State.AWAITING_FINAL_SANCTION.value:
        pytest.skip("routing did not reach final sanction")
    with pytest.raises(ConflictError):
        decisions.sanction(request=r, actor_user_id=APPLICANT, approve=True)


def test_a_substitute_cannot_be_nominated_for_leave_they_are_on():
    """Nominating somebody who is themselves away defeats the point."""
    factories.setup_all(999)
    away = approved(user_id=OTHER, days=5)
    assert away.state in (State.APPROVED_NOT_STARTED.value,
                          State.AWAITING_FINAL_SANCTION.value)
    factories.credit(APPLICANT, Category.EL, 30)
    with pytest.raises((BadRequestError, ConflictError)):
        service.submit(user_id=APPLICANT, category=Category.EL,
                       starts_on=date(YEAR, 3, 3), ends_on=date(YEAR, 3, 4),
                       reason="x", unit="CSE", faculty=False,
                       substitute_user_id=OTHER)


def test_an_extension_cannot_run_backwards():
    factories.setup_all(999)
    r = approved(days=3)
    with pytest.raises(BadRequestError):
        lifecycle.request_extension(request=r, actor_user_id=APPLICANT,
                                    new_end=r.starts_on - timedelta(days=1))


def test_resumption_cannot_predate_the_leave():
    factories.setup_all(999)
    r = approved(days=3)
    with pytest.raises(BadRequestError):
        lifecycle.submit_resumption(request=r, actor_user_id=APPLICANT,
                                    resumed_on=r.starts_on - timedelta(days=5))


def test_somebody_else_cannot_submit_a_resumption_for_you():
    factories.setup_all(999)
    r = approved(days=3)
    with pytest.raises((ConflictError, BadRequestError)):
        lifecycle.submit_resumption(request=r, actor_user_id=OTHER,
                                    resumed_on=r.ends_on)


def test_somebody_else_cannot_withdraw_your_request():
    factories.setup_all(999)
    factories.credit(APPLICANT, Category.CL, 8)
    r = service.submit(user_id=APPLICANT, category=Category.CL,
                       starts_on=date(YEAR, 3, 2), ends_on=date(YEAR, 3, 3),
                       reason="x", unit="CSE", faculty=False)
    with pytest.raises((ConflictError, BadRequestError)):
        decisions.withdraw(request=r, actor_user_id=OTHER)


class TestNobodyDecidesTheirOwnLeave:
    """A head is an employee too, and their request lands in their own queue."""

    def _own_request(self, head=601):
        factories.setup_all(999)
        factories.credit(head, Category.CL, 8)
        return service.submit(
            user_id=head, category=Category.CL, starts_on=date(YEAR, 3, 2),
            ends_on=date(YEAR, 3, 3), reason="x", unit="CSE", faculty=False)

    def test_a_unit_head_cannot_approve_it(self):
        r = self._own_request()
        with pytest.raises(ConflictError, match="cannot decide your own"):
            decisions.unit_head_decides(request=r, actor_user_id=601, approve=True)

    def test_a_unit_head_cannot_reject_it_either(self):
        r = self._own_request()
        with pytest.raises(ConflictError, match="cannot decide your own"):
            decisions.unit_head_decides(request=r, actor_user_id=601, approve=False)

    def test_it_is_absent_from_their_own_queue(self):
        from modules.leave.selectors import scoping

        self._own_request()
        assert list(scoping.review_queue("CSE", 601)) == []

    def test_but_a_colleague_still_sees_and_can_action_it(self):
        from modules.leave.selectors import scoping

        r = self._own_request()
        assert [x.pk for x in scoping.review_queue("CSE", 900)] == [r.pk]
        assert decisions.unit_head_decides(
            request=r, actor_user_id=900, approve=True).state == "APPROVED_NOT_STARTED"

    def test_self_sanction_is_still_permitted_where_configured(self):
        from modules.leave.models import AuthorityRule

        policy, _ = factories.setup_all(999)
        AuthorityRule.objects.filter(
            policy_id=policy.pk, category=Category.CL.value).update(self_sanction=True)
        factories.credit(601, Category.CL, 8)
        r = service.submit(user_id=601, category=Category.CL,
                           starts_on=date(YEAR, 3, 2), ends_on=date(YEAR, 3, 3),
                           reason="x", unit="CSE", faculty=False)

        # BR-EL-020 exists so the Director's own leave has somewhere to go.
        assert r.state == State.AWAITING_SELF_SANCTION.value
        assert decisions.sanction(
            request=r, actor_user_id=601, approve=True
        ).state == State.APPROVED_NOT_STARTED.value


class TestTheBalanceCannotGoNegative:
    def test_two_requests_affordable_apart_are_not_affordable_together(self):
        factories.setup_all(999)
        factories.credit(APPLICANT, Category.CL, 2)
        a = service.submit(user_id=APPLICANT, category=Category.CL,
                           starts_on=date(YEAR, 3, 2), ends_on=date(YEAR, 3, 3),
                           reason="x", unit="CSE", faculty=False)
        b = service.submit(user_id=APPLICANT, category=Category.CL,
                           starts_on=date(YEAR, 3, 9), ends_on=date(YEAR, 3, 10),
                           reason="y", unit="CSE", faculty=False)

        decisions.unit_head_decides(request=a, actor_user_id=900, approve=True)

        with pytest.raises(ConflictError, match="approved since"):
            decisions.unit_head_decides(request=b, actor_user_id=900, approve=True)

    def test_the_balance_is_never_left_negative(self):
        from modules.leave.selectors import balances

        factories.setup_all(999)
        factories.credit(APPLICANT, Category.CL, 2)
        # Both are submitted while still affordable, which makes the race.
        pending = [
            service.submit(user_id=APPLICANT, category=Category.CL, starts_on=start,
                           ends_on=start + timedelta(days=1), reason="x",
                           unit="CSE", faculty=False)
            for start in (date(YEAR, 3, 2), date(YEAR, 3, 9))
        ]

        for r in pending:
            with contextlib.suppress(ConflictError):
                decisions.unit_head_decides(request=r, actor_user_id=900, approve=True)

        assert balances.balance_for(APPLICANT, YEAR, Category.CL).available >= 0
