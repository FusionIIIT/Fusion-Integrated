"""Real threads against the real database: balance must never go negative."""
import threading
from datetime import timedelta

import pytest
from django.db import connection

from conftest import make_principal
from core.api.exceptions import DomainError
from modules.elm.models import LeaveRequest
from modules.elm.services import requests as svc
from modules.elm.tests.conftest import EMPLOYEE, FAC, monday, people

pytestmark = pytest.mark.django_db(transaction=True)


def test_parallel_applications_cannot_overspend(stub_iam, policy, calendar):
    stub_iam(users=people())
    actor = make_principal(user_id=FAC, kind="faculty", permissions=EMPLOYEE,
                           modules=("elm",), roles=("faculty",), active_role="faculty")
    results = []

    def go(week):
        start = monday(week)
        try:
            svc.apply(actor, svc.LeaveInput(category="CL", start_date=start,
                                            end_date=start + timedelta(days=4),
                                            purpose="x"))
            results.append("ok")
        except DomainError as exc:
            results.append(type(exc).__name__)
        finally:
            connection.close()

    threads = [threading.Thread(target=go, args=(w,)) for w in (2, 4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results.count("ok") == 1, results
    assert LeaveRequest.objects.filter(user_id=FAC).count() == 1
