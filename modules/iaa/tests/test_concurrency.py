from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.db import close_old_connections

from modules.iaa import services
from modules.iaa.domain.rules import Role
from modules.iaa.models import Anomaly, Budget, FinancialRequest
from modules.iaa.tests.conftest import FINANCE, submitted


@pytest.mark.django_db(transaction=True)
def test_two_simultaneous_finance_validations_cannot_overreserve_budget(world, client_as):
    Budget.objects.update(allocated=150)
    ids = [submitted(client_as), submitted(client_as)]
    barrier = Barrier(2)

    def worker(pk):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            req = services.validate_finance(
                services.Context(FINANCE, Role.FINANCE), pk, remarks="Concurrent financial review"
            )
            return req.status
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        states = list(pool.map(worker, ids))
    assert sorted(states) == ["finance_validated", "submitted"]
    assert sum(FinancialRequest.objects.values_list("reservation", flat=True)) == 100
    assert Anomaly.objects.filter(category="budget", automatic=True).count() == 1
