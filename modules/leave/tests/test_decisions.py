"""The approval path, and what it does to the balance."""
from datetime import date
from decimal import Decimal

import pytest

from core.api.exceptions import ConflictError
from modules.leave.domain.categories import Category
from modules.leave.domain.state_machine import State
from modules.leave.models import EntryReason
from modules.leave.selectors import balances
from modules.leave.services import decisions
from modules.leave.services import requests as service
from modules.leave.tests.factories import setup_all

pytestmark = pytest.mark.django_db

USER, HEAD, ESTT, AUTH, SUB = 501, 601, 602, 603, 777
D = Decimal


@pytest.fixture
def configured():
    return setup_all(USER)


def cl_request(**kw):
    return service.submit(
        user_id=USER,
        category=Category.CL,
        starts_on=date(2026, 9, 1),
        ends_on=date(2026, 9, 2),
        reason="personal",
        faculty=False,
        **kw,
    )


def el_request(**kw):
    return service.submit(
        user_id=USER,
        category=Category.EL,
        starts_on=date(2026, 9, 7),
        ends_on=date(2026, 9, 11),
        reason="travel",
        faculty=False,
        **kw,
    )


class TestUnitHeadFinal:
    """BR-EL-016. Casual leave ends with the unit head."""

    def test_approval_closes_the_request(self, configured):
        r = decisions.unit_head_decides(request=cl_request(), actor_user_id=HEAD, approve=True)
        assert r.state == State.APPROVED_NOT_STARTED.value

    def test_approval_deducts_the_days(self, configured):
        before = balances.available(USER, 2026, Category.CL)
        decisions.unit_head_decides(request=cl_request(), actor_user_id=HEAD, approve=True)
        assert balances.available(USER, 2026, Category.CL) == before - D(2)

    def test_the_deduction_is_a_ledger_row_naming_the_request(self, configured):
        r = decisions.unit_head_decides(request=cl_request(), actor_user_id=HEAD, approve=True)
        rows = balances.statement(USER, 2026, Category.CL)
        charged = [e for e in rows if e.reason == EntryReason.CONSUMED]
        assert len(charged) == 1
        assert charged[0].request_id == r.pk
        assert charged[0].days == D(-2)
        assert charged[0].policy_id == r.policy_id

    def test_rejection_leaves_the_balance_alone(self, configured):
        before = balances.available(USER, 2026, Category.CL)
        r = decisions.unit_head_decides(request=cl_request(), actor_user_id=HEAD, approve=False)
        assert r.state == State.REJECTED.value
        assert balances.available(USER, 2026, Category.CL) == before


class TestHigherSanction:
    """BR-EL-017 to BR-EL-019. Earned leave passes through the hierarchy."""

    def test_the_unit_head_only_recommends(self, configured):
        r = decisions.unit_head_decides(request=el_request(), actor_user_id=HEAD, approve=True)
        assert r.state == State.AWAITING_ESTABLISHMENT.value

    def test_recommendation_does_not_deduct(self, configured):
        before = balances.available(USER, 2026, Category.EL)
        decisions.unit_head_decides(request=el_request(), actor_user_id=HEAD, approve=True)
        assert balances.available(USER, 2026, Category.EL) == before

    def test_the_full_path_ends_in_approval(self, configured):
        r = el_request()
        r = decisions.unit_head_decides(request=r, actor_user_id=HEAD, approve=True)
        r = decisions.establishment_routes(request=r, actor_user_id=ESTT)
        assert r.state == State.AWAITING_FINAL_SANCTION.value
        r = decisions.sanction(request=r, actor_user_id=AUTH, approve=True)
        assert r.state == State.APPROVED_NOT_STARTED.value
        assert balances.available(USER, 2026, Category.EL) == D(30) - D(5)

    def test_the_trail_records_every_hand(self, configured):
        r = el_request()
        r = decisions.unit_head_decides(request=r, actor_user_id=HEAD, approve=True)
        r = decisions.establishment_routes(request=r, actor_user_id=ESTT)
        r = decisions.sanction(request=r, actor_user_id=AUTH, approve=True)
        actors = [t.actor_user_id for t in r.transitions.order_by("id")]
        assert actors == [USER, HEAD, ESTT, AUTH]


class TestSubstitute:
    """BR-EL-015. Routing waits for the answer."""

    def test_acceptance_releases_the_request(self, configured):
        r = cl_request(substitute_user_id=SUB)
        r = decisions.substitute_responds(request=r, substitute_user_id=SUB, accepted=True)
        assert r.state == State.AWAITING_UNIT_HEAD.value

    def test_a_decline_returns_it_to_the_applicant(self, configured):
        r = cl_request(substitute_user_id=SUB)
        r = decisions.substitute_responds(request=r, substitute_user_id=SUB, accepted=False)
        assert r.state == State.APPLICANT_ACTION_REQUIRED.value

    def test_a_stranger_cannot_answer(self, configured):
        from core.api.exceptions import NotFoundError

        r = cl_request(substitute_user_id=SUB)
        with pytest.raises(NotFoundError):
            decisions.substitute_responds(request=r, substitute_user_id=999, accepted=True)

    def test_renomination_asks_someone_else(self, configured):
        r = cl_request(substitute_user_id=SUB)
        r = decisions.substitute_responds(request=r, substitute_user_id=SUB, accepted=False)
        r = decisions.renominate(request=r, actor_user_id=USER, substitute_user_id=888)
        assert r.state == State.AWAITING_SUBSTITUTE.value
        assert r.nominations.count() == 2


class TestRefusals:
    def test_an_approved_request_cannot_be_withdrawn(self, configured):
        r = decisions.unit_head_decides(request=cl_request(), actor_user_id=HEAD, approve=True)
        with pytest.raises(ConflictError) as exc:
            decisions.withdraw(request=r, actor_user_id=USER)
        assert exc.value.code == "illegal_transition"

    def test_only_the_applicant_withdraws(self, configured):
        with pytest.raises(ConflictError) as exc:
            decisions.withdraw(request=cl_request(), actor_user_id=HEAD)
        assert exc.value.code == "not_applicant"

    def test_a_pending_request_may_be_withdrawn(self, configured):
        r = decisions.withdraw(request=cl_request(), actor_user_id=USER)
        assert r.state == State.WITHDRAWN.value

    def test_a_decided_request_accepts_nothing_further(self, configured):
        r = decisions.unit_head_decides(request=cl_request(), actor_user_id=HEAD, approve=False)
        with pytest.raises(ConflictError) as exc:
            decisions.unit_head_decides(request=r, actor_user_id=HEAD, approve=True)
        assert exc.value.code == "request_closed"

    def test_the_unit_head_cannot_perform_the_final_sanction(self, configured):
        r = decisions.unit_head_decides(request=el_request(), actor_user_id=HEAD, approve=True)
        r = decisions.establishment_routes(request=r, actor_user_id=ESTT)
        with pytest.raises(ConflictError) as exc:
            decisions.unit_head_decides(request=r, actor_user_id=HEAD, approve=True)
        assert exc.value.code == "illegal_transition"
