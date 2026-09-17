"""The accounting must survive being run twice, late, or out of order."""
from datetime import date
from decimal import Decimal as D

import pytest

from core.api.exceptions import ConflictError
from modules.leave.domain.categories import Category
from modules.leave.domain.state_machine import State
from modules.leave.models import EntryReason, LedgerEntry, YearEndClosure
from modules.leave.selectors import balances
from modules.leave.services import decisions, lifecycle, yearend
from modules.leave.services import requests as service
from modules.leave.tests import factories
from modules.leave.tests.factories import YEAR

pytestmark = pytest.mark.django_db

#: The factory routes everything above the unit head to the Registrar.
REGISTRAR = frozenset({"Registrar"})
U = 701


def test_closing_a_carry_only_account_twice_is_refused():
    factories.make_policy()
    factories.credit(U, Category.EL, 10)
    yearend.close(user_id=U, year=YEAR, faculty=False)
    opening_after_one = balances.balance_for(U, YEAR + 1, Category.EL).available
    with pytest.raises(ConflictError):
        yearend.close(user_id=U, year=YEAR, faculty=False)
    assert balances.balance_for(U, YEAR + 1, Category.EL).available == opening_after_one


def test_a_movement_cannot_be_booked_into_a_closed_year():
    """The December request approved in January."""
    factories.setup_all(U)
    pending = service.submit(
        user_id=U, category=Category.CL, starts_on=date(YEAR, 12, 28),
        ends_on=date(YEAR, 12, 29), reason="x", unit="CSE", faculty=False,
        designations=frozenset({"Assistant Professor"}))

    yearend.close(user_id=U, year=YEAR, faculty=False)

    with pytest.raises(ConflictError, match="has been closed"):
        decisions.unit_head_decides(request=pending, actor_user_id=900, approve=True)


def test_revoking_after_close_is_refused():
    factories.make_policy()
    factories.credit(U, Category.CL, 8)
    yearend.close(user_id=U, year=YEAR, faculty=False)
    with pytest.raises(ConflictError):
        yearend.revoke_credit(user_id=U, year=YEAR, actor_user_id=0, note="x")
    assert balances.balance_for(U, YEAR, Category.CL).available >= 0


def test_extension_moves_the_end_date():
    factories.setup_all(U)
    factories.credit(U, Category.EL, 30)
    r = service.submit(user_id=U, category=Category.EL, starts_on=date(YEAR, 8, 10),
                       ends_on=date(YEAR, 8, 17), reason="x", unit="CSE", faculty=False)
    r = decisions.unit_head_decides(request=r, actor_user_id=900, approve=True)
    if r.state == State.AWAITING_ESTABLISHMENT.value:
        r = decisions.establishment_routes(request=r, actor_user_id=901)
    if r.state == State.AWAITING_FINAL_SANCTION.value:
        r = decisions.sanction(request=r, actor_user_id=902, approve=True,
                                actor_designations=REGISTRAR)
    r.state = State.ONGOING.value
    r.save(update_fields=["state"])
    r = lifecycle.request_extension(request=r, actor_user_id=U, new_end=date(YEAR, 8, 20))
    while r.state.startswith("EXTENSION"):
        if r.state == State.EXTENSION_AWAITING_UNIT_HEAD.value:
            r = lifecycle.recommend_extension(request=r, actor_user_id=900)
        elif r.state == State.EXTENSION_AWAITING_ESTABLISHMENT.value:
            r = lifecycle.route_extension(request=r, actor_user_id=901)
        elif r.state == State.EXTENSION_AWAITING_FINAL.value:
            r = lifecycle.decide_extension(request=r, actor_user_id=902, approve=True)
        else:
            break
    r.refresh_from_db()
    assert r.ends_on == date(YEAR, 8, 20), f"ends_on stayed {r.ends_on}"


def test_a_carry_only_close_is_still_recorded_as_closed():
    """The case that made closing look un-run."""
    factories.make_policy()
    factories.credit(U, Category.EL, 10)

    yearend.close(user_id=U, year=YEAR, faculty=False)

    assert not LedgerEntry.objects.filter(year=YEAR, reason=EntryReason.LAPSED).exists()
    assert YearEndClosure.objects.filter(user_id=U, year=YEAR).exists()
    assert yearend.already_closed(U, YEAR)


def test_the_closure_records_what_moved():
    factories.make_policy()
    factories.credit(U, Category.EL, 10)
    factories.credit(U, Category.CL, 8)

    yearend.close(user_id=U, year=YEAR, faculty=False)

    closure = YearEndClosure.objects.get(user_id=U, year=YEAR)
    assert closure.carried == D(10)
    assert closure.lapsed == D(8)


def test_a_second_close_is_refused_by_the_database_not_by_a_prior_read():
    from django.db import IntegrityError

    factories.make_policy()
    factories.credit(U, Category.EL, 10)
    yearend.close(user_id=U, year=YEAR, faculty=False)

    # Two schedulers racing get one closure and one loser.
    with pytest.raises(IntegrityError):
        YearEndClosure.objects.create(user_id=U, year=YEAR)


def test_an_extension_charges_only_the_additional_days():
    factories.setup_all(U)
    factories.credit(U, Category.EL, 30)
    r = service.submit(user_id=U, category=Category.EL, starts_on=date(YEAR, 8, 10),
                       ends_on=date(YEAR, 8, 17), reason="x", unit="CSE", faculty=False)
    r = decisions.unit_head_decides(request=r, actor_user_id=900, approve=True)
    if r.state == State.AWAITING_ESTABLISHMENT.value:
        r = decisions.establishment_routes(request=r, actor_user_id=901)
    if r.state == State.AWAITING_FINAL_SANCTION.value:
        r = decisions.sanction(request=r, actor_user_id=902, approve=True,
                                actor_designations=REGISTRAR)
    original = r.requested_days
    r.state = State.ONGOING.value
    r.save(update_fields=["state"])

    r = lifecycle.request_extension(request=r, actor_user_id=U,
                                    new_end=date(YEAR, 8, 20))
    # The date is held in a field, not parsed back out of a remark.
    assert r.extension_to == date(YEAR, 8, 20)

    while r.state.startswith("EXTENSION"):
        if r.state == State.EXTENSION_AWAITING_UNIT_HEAD.value:
            r = lifecycle.recommend_extension(request=r, actor_user_id=900)
        elif r.state == State.EXTENSION_AWAITING_ESTABLISHMENT.value:
            r = lifecycle.route_extension(request=r, actor_user_id=901)
        elif r.state == State.EXTENSION_AWAITING_FINAL.value:
            r = lifecycle.decide_extension(request=r, actor_user_id=902, approve=True)
        else:
            break

    r.refresh_from_db()
    assert r.ends_on == date(YEAR, 8, 20)
    assert r.requested_days > original
    assert r.extension_to is None


def test_a_refused_extension_leaves_the_leave_as_it_was():
    factories.setup_all(U)
    factories.credit(U, Category.EL, 30)
    r = service.submit(user_id=U, category=Category.EL, starts_on=date(YEAR, 8, 10),
                       ends_on=date(YEAR, 8, 17), reason="x", unit="CSE", faculty=False)
    r = decisions.unit_head_decides(request=r, actor_user_id=900, approve=True)
    if r.state == State.AWAITING_ESTABLISHMENT.value:
        r = decisions.establishment_routes(request=r, actor_user_id=901)
    if r.state == State.AWAITING_FINAL_SANCTION.value:
        r = decisions.sanction(request=r, actor_user_id=902, approve=True,
                                actor_designations=REGISTRAR)
    r.state = State.ONGOING.value
    r.save(update_fields=["state"])
    r = lifecycle.request_extension(request=r, actor_user_id=U,
                                    new_end=date(YEAR, 8, 20))
    while r.state not in (State.EXTENSION_AWAITING_FINAL.value, State.ONGOING.value):
        if r.state == State.EXTENSION_AWAITING_UNIT_HEAD.value:
            r = lifecycle.recommend_extension(request=r, actor_user_id=900)
        elif r.state == State.EXTENSION_AWAITING_ESTABLISHMENT.value:
            r = lifecycle.route_extension(request=r, actor_user_id=901)
        else:
            break

    r = lifecycle.decide_extension(request=r, actor_user_id=902, approve=False)

    r.refresh_from_db()
    assert r.ends_on == date(YEAR, 8, 17)
    assert r.extension_to is None
