"""Two callers reading the same state before either has written it.

Real threads on real connections, released together on a Barrier, under
`django_db(transaction=True)` — the usual per-test transaction would hide each thread's
writes from the other and the tests would pass without touching what they are about
(testing-strategy.md). Postgres only: sqlite serialises everything and makes this vacuous.
"""
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from django.db import connection

from core.api.exceptions import ConflictError
from modules.mms.services import operations as svc
from modules.mms.tests import factories as f
from modules.mms.tests.helpers import caretaker

pytestmark = pytest.mark.django_db(transaction=True)


def _race(*calls):
    """Run each callable on its own thread, all released at once. Returns ['ok' | exc]."""
    barrier = threading.Barrier(len(calls))

    def run(call):
        try:
            barrier.wait(timeout=10)
            call()
        except Exception as exc:                       # noqa: BLE001 — the outcome IS the data
            return exc
        else:
            return "ok"
        finally:
            connection.close()                         # each thread owns a connection

    with ThreadPoolExecutor(len(calls)) as pool:
        return list(pool.map(run, calls))


def _winners_and_conflicts(outcomes):
    return outcomes.count("ok"), sum(isinstance(o, ConflictError) for o in outcomes)


def test_two_caretakers_deciding_one_registration_yield_exactly_one_decision():
    r = f.RegistrationFactory()
    outcomes = _race(
        lambda: svc.review_registration_request(actor=caretaker(), request_id=r.pk,
                                                action="approve"),
        lambda: svc.review_registration_request(actor=caretaker(), request_id=r.pk,
                                                action="reject"))
    assert _winners_and_conflicts(outcomes) == (1, 1), outcomes
    r.refresh_from_db()
    assert r.status in {"approved", "rejected"}
    # and exactly one notification, from the one decision that stuck
    from modules.mms.models import MmsNotification
    assert MmsNotification.objects.filter(event_type__startswith="registration_").count() == 1


def test_a_caretaker_decision_racing_the_default_rejection_has_one_winner():
    """UC-020 vs UC-029: whichever commits first wins; the loser must not overwrite it."""
    r = f.SpecialFoodFactory()
    outcomes = _race(
        lambda: svc.review_special_food_request(actor=caretaker(), request_id=r.pk,
                                                action="approve"),
        lambda: svc.default_reject_special_food_request(request_id=r.pk))
    r.refresh_from_db()
    if r.status == "approved":
        assert r.is_default_rejected is False
    else:
        assert (r.status, r.is_default_rejected) == ("rejected", True)
    assert not [o for o in outcomes if isinstance(o, Exception) and not isinstance(o, ConflictError)]


def test_two_concurrent_deregistration_approvals_do_not_double_apply():
    dr = f.DeregistrationFactory()
    outcomes = _race(
        lambda: svc.review_deregistration_request(actor=caretaker(), request_id=dr.pk,
                                                  action="approve"),
        lambda: svc.review_deregistration_request(actor=caretaker(), request_id=dr.pk,
                                                  action="approve"))
    assert _winners_and_conflicts(outcomes) == (1, 1), outcomes


def test_concurrent_fulfilment_updates_cannot_both_serve_and_cancel():
    r = f.SpecialFoodFactory(approved=True)
    from modules.mms.domain.state_machine import InvalidTransition
    outcomes = _race(
        lambda: svc.update_special_food_fulfillment(actor=caretaker(), request_id=r.pk,
                                                    status="served"),
        lambda: svc.update_special_food_fulfillment(actor=caretaker(), request_id=r.pk,
                                                    status="cancelled"))
    assert outcomes.count("ok") == 1
    assert sum(isinstance(o, InvalidTransition) for o in outcomes) == 1, outcomes
    r.refresh_from_db()
    assert (r.served_at is None) != (r.cancelled_at is None)       # exactly one stamp
