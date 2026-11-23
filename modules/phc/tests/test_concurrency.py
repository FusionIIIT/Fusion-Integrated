from threading import Barrier, Thread

import pytest
from django.db import close_old_connections

from core.api.exceptions import ConflictError
from modules.phc.models import InventoryItem, InventoryMovement
from modules.phc.services.inventory import adjust_stock

pytestmark = pytest.mark.django_db(transaction=True)


def test_phc_br_07_concurrent_deductions_cannot_make_stock_negative():
    item = InventoryItem.objects.create(name="Test stock", unit="unit",
                                        reorder_threshold=1)
    adjust_stock(item_id=item.pk, quantity_delta=1,
                 reason="Initial stock", actor_user_id=1)
    barrier = Barrier(2)
    results = []

    def deduct():
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            adjust_stock(item_id=item.pk, quantity_delta=-1,
                         reason="Concurrent dispense", actor_user_id=2)
            results.append("updated")
        except ConflictError:
            results.append("refused")
        finally:
            close_old_connections()

    threads = [Thread(target=deduct) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=20)

    assert all(not thread.is_alive() for thread in threads)
    assert sorted(results) == ["refused", "updated"]
    assert sum(InventoryMovement.objects.filter(item=item)
               .values_list("quantity_delta", flat=True)) == 0
