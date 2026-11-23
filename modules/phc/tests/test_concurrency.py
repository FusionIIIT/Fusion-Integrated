"""Real threads against the real database for anything that must happen once."""
import threading
from decimal import Decimal

import pytest
from django.db import connection
from django.utils import timezone

from conftest import make_principal
from core.api.exceptions import DomainError
from modules.phc.models import ClaimAction, ReimbursementClaim, StockAdjustment
from modules.phc.registry import ROLE_GRANTS
from modules.phc.services import inventory, reimbursements
from modules.phc.tests.factories import EMPLOYEE_ID, PHC_STAFF_ID, item, visit_for

pytestmark = pytest.mark.django_db(transaction=True)


def _race(fn, n=2):
    barrier = threading.Barrier(n)
    results = []

    def run():
        try:
            barrier.wait()
            results.append(("ok", fn()))
        except DomainError as exc:
            results.append(("refused", exc.code))
        finally:
            connection.close()

    threads = [threading.Thread(target=run) for _ in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results


# PHC-BR-08
def test_a_claim_moves_once_when_two_reviewers_race_phc_br_08():
    visit = visit_for(EMPLOYEE_ID)
    claim = ReimbursementClaim.objects.create(
        user_id=EMPLOYEE_ID, prescription=visit.prescriptions.get(),
        expense_date=timezone.localdate(), amount="10.00", submitted_at=timezone.now())
    staff = make_principal(user_id=PHC_STAFF_ID, kind="staff", modules=("phc",),
                           permissions=ROLE_GRANTS["PHC Staff"])
    results = _race(lambda: reimbursements.transition_claim(actor=staff, claim_id=claim.pk,
                                                            event="forward"))
    assert sorted(r[0] for r in results) == ["ok", "refused"]
    assert ClaimAction.objects.filter(claim=claim, event="forward").count() == 1


def test_concurrent_deductions_never_drive_stock_negative():
    stock = item(level="10", threshold="0")
    staff = make_principal(user_id=PHC_STAFF_ID, kind="staff", modules=("phc",),
                           permissions=ROLE_GRANTS["PHC Staff"])
    results = _race(lambda: inventory.adjust_stock(actor=staff, item_id=stock.pk,
                                                   delta=Decimal("-7"), reason=""), n=3)
    assert [r[0] for r in results].count("ok") == 1
    stock.refresh_from_db()
    assert stock.stock_level == Decimal("3")
    assert StockAdjustment.objects.filter(item=stock).count() == 1


# PHC-UC-16 E1
def test_two_authorities_racing_on_one_requisition_decide_it_once():
    from modules.phc.models import Notification, Requisition
    from modules.phc.services import requisitions

    stock = item()
    req = Requisition.objects.create(originator_user_id=PHC_STAFF_ID, purpose="restock")
    req.lines.create(item=stock, quantity="5")
    authorities = [make_principal(user_id=5001 + i, kind="faculty", modules=("phc",),
                                  permissions=ROLE_GRANTS["Approving Authority"])
                   for i in range(2)]
    events = iter(["approve", "reject"])
    lock = threading.Lock()

    def decide():
        with lock:
            actor, event = authorities.pop(), next(events)
        return requisitions.transition(actor=actor, requisition_id=req.pk, event=event)

    results = _race(decide)
    assert sorted(r[0] for r in results) == ["ok", "refused"]
    assert Notification.objects.filter(resource_type="requisition",
                                       resource_id=req.pk).count() == 1
