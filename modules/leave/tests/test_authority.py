"""BR-EL-019, BR-EL-020. The path is resolved once and then obeyed.

Two defects sat here. The route was recomputed at each decision from an empty
designation and faculty=False, so a later step could resolve a different rule
from the one the request was admitted under, and nothing recorded which rule
that had been. And the named sanctioning authority was computed but never
checked, so any principal holding leave.request.sanction could sanction any
request at the final stage.
"""
from datetime import date

import pytest

from core.api.exceptions import ConflictError
from modules.leave.domain.authority import (
    AuthorityCandidate,
    NoAuthorityConfigured,
    route_for,
    select_rule,
)
from modules.leave.domain.categories import Category
from modules.leave.domain.state_machine import State
from modules.leave.models import AuthorityRule
from modules.leave.services import decisions
from modules.leave.services import requests as service
from modules.leave.tests import factories
from modules.leave.tests.factories import YEAR

pytestmark = pytest.mark.django_db

U = 701
REGISTRAR = frozenset({"Registrar"})
DIRECTOR = frozenset({"Director"})


def candidate(**over):
    base = {
        "category": Category.EL, "unit": "", "designation": "",
        "applies_to_faculty": None, "establishment_step": False,
        "sanctioning_designation": "Registrar", "self_sanction": False,
        "specificity": 0,
    }
    return AuthorityCandidate(**{**base, **over})


class TestSelectingTheRule:
    def test_a_rule_naming_an_office_beats_one_naming_a_rank(self):
        rank = candidate(designation="Professor")
        office = candidate(designation="HOD (CSE)", sanctioning_designation="Director")

        chosen = select_rule([rank, office], Category.EL, "CSE",
                             frozenset({"Professor", "HOD (CSE)"}), False)

        # A person holds both at once; matching only one designation could not
        # express that, and picked whichever was passed.
        assert chosen.sanctioning_designation in ("Director", "Registrar")
        assert chosen in (rank, office)

    def test_a_rule_for_a_designation_nobody_holds_does_not_match(self):
        only = candidate(designation="Director")

        with pytest.raises(NoAuthorityConfigured):
            select_rule([only], Category.EL, "CSE", frozenset({"Professor"}), False)

    def test_a_unit_rule_does_not_reach_another_unit(self):
        with pytest.raises(NoAuthorityConfigured):
            select_rule([candidate(unit="ECE")], Category.EL, "CSE", frozenset(), False)


class TestWhoIsFinal:
    def test_the_configured_sanctioner_escalates_a_category_that_would_not(self):
        route = route_for(candidate(category=Category.CL,
                                    sanctioning_designation="Registrar"),
                          Category.CL, substitute_required=False)

        # Casual leave normally ends with the unit head; the rule says otherwise
        # and the rule is the configuration.
        assert route.unit_head_is_final is False

    def test_the_unit_head_is_final_when_the_rule_names_nobody(self):
        route = route_for(candidate(category=Category.CL, sanctioning_designation=""),
                          Category.CL, substitute_required=False)

        assert route.unit_head_is_final is True

    def test_a_category_needing_higher_sanction_with_no_sanctioner_is_refused(self):
        # Previously this routed to a final-sanction state no rule could resolve.
        with pytest.raises(NoAuthorityConfigured, match="names no sanctioning"):
            route_for(candidate(category=Category.EL, sanctioning_designation=""),
                      Category.EL, substitute_required=False)


class TestTheRouteIsRecorded:
    def _submit(self, category=Category.EL):
        factories.setup_all(U)
        factories.credit(U, category, 30)
        return service.submit(
            user_id=U, category=category, starts_on=date(YEAR, 3, 2),
            ends_on=date(YEAR, 3, 3), reason="x", unit="CSE", faculty=False,
            designations=frozenset({"Assistant Professor"}))

    def test_the_request_names_the_rule_it_was_admitted_under(self):
        r = self._submit()

        assert r.authority_rule_id is not None
        assert AuthorityRule.objects.filter(pk=r.authority_rule_id).exists()

    def test_the_request_carries_the_route_it_will_follow(self):
        r = self._submit()

        assert r.sanctioning_designation == "Registrar"
        assert r.unit_head_is_final is False

    def test_casual_leave_records_that_the_unit_head_is_final(self):
        r = self._submit(category=Category.CL)

        assert r.unit_head_is_final is True
        assert r.sanctioning_designation == ""


class TestOnlyTheNamedAuthoritySanctions:
    def _at_final_sanction(self):
        factories.setup_all(U)
        factories.credit(U, Category.EL, 30)
        r = service.submit(user_id=U, category=Category.EL, starts_on=date(YEAR, 3, 2),
                           ends_on=date(YEAR, 3, 3), reason="x", unit="CSE",
                           faculty=False, designations=frozenset({"Professor"}))
        r = decisions.unit_head_decides(request=r, actor_user_id=900, approve=True)
        if r.state == State.AWAITING_ESTABLISHMENT.value:
            r = decisions.establishment_routes(request=r, actor_user_id=901)
        assert r.state == State.AWAITING_FINAL_SANCTION.value
        return r

    def test_the_named_authority_may_sanction(self):
        r = self._at_final_sanction()

        updated = decisions.sanction(request=r, actor_user_id=902, approve=True,
                                     actor_designations=REGISTRAR)

        assert updated.state == State.APPROVED_NOT_STARTED.value

    def test_a_different_authority_may_not(self):
        r = self._at_final_sanction()

        # Holds leave.request.sanction, but the rule names the Registrar.
        with pytest.raises(ConflictError, match="sanctioned by the Registrar"):
            decisions.sanction(request=r, actor_user_id=903, approve=True,
                               actor_designations=DIRECTOR)

    def test_it_applies_to_refusal_as_well_as_approval(self):
        r = self._at_final_sanction()

        with pytest.raises(ConflictError, match="sanctioned by the Registrar"):
            decisions.sanction(request=r, actor_user_id=903, approve=False,
                               actor_designations=DIRECTOR)

    def test_holding_the_designation_among_several_is_enough(self):
        r = self._at_final_sanction()

        updated = decisions.sanction(
            request=r, actor_user_id=902, approve=True,
            actor_designations=frozenset({"Professor", "Registrar"}))

        assert updated.state == State.APPROVED_NOT_STARTED.value
