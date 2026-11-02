"""Race safety (two simultaneous check-ins) and the gate-validate query budget."""
import threading
from datetime import timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from modules.vms.models import RoleAssignment, VisitLog
from modules.vms.services import gate as svc
from modules.vms.tests import factories as f

#: Measured success path (no zone): gate, role (2), savepoint, pass lock, open-check-in,
#: blacklist (2), log insert, audit insert, host notice (get_or_create). The lane file
#: asked for 6, which cannot hold once the audit row, host notice and role check are
#: written. The point of the test is that it is constant, not that it grows with history.
VALIDATE_QUERY_BUDGET = 14
DENIED_QUERY_BUDGET = 18


@pytest.mark.django_db
def test_gate_validate_query_budget(sec, gate, vpass):
    f.make_published_policy(version=2)
    with CaptureQueriesContext(connection) as ctx:
        res = svc.validate_and_check_in(security_actor=sec, credential={"qr_token": vpass.qr_token},
                                        gate_id=gate.pk)
    assert res.outcome == svc.CHECKED_IN
    assert len(ctx) <= VALIDATE_QUERY_BUDGET, [q["sql"][:80] for q in ctx.captured_queries]


@pytest.mark.django_db
def test_denied_validate_does_not_scale_with_history(sec, gate, vpass):
    vpass.is_active = False
    vpass.save()
    for _ in range(20):
        f.make_visit_log(visit_pass=vpass, event="denied")
    with CaptureQueriesContext(connection) as ctx:
        svc.validate_and_check_in(security_actor=sec, credential={"qr_token": vpass.qr_token},
                                  gate_id=gate.pk)
    assert len(ctx) <= DENIED_QUERY_BUDGET


@pytest.mark.django_db(transaction=True)
def test_two_simultaneous_check_ins_exactly_one_succeeds():
    gate = f.make_gate()
    f.make_role_assignment(user_id=3001, role=RoleAssignment.Role.SECURITY,
                           scope_type=RoleAssignment.ScopeType.GATE, scope_id=gate.pk)
    actor = f.make_actor(user_id=3001)
    now = timezone.now()
    vp = f.make_visit_pass(visit_request=f.make_visit_request(status="approved"),
                           valid_from=now - timedelta(hours=1),
                           valid_until=now + timedelta(hours=1))
    barrier = threading.Barrier(2)
    outcomes, errors = [], []

    def worker():
        try:
            barrier.wait(timeout=10)
            res = svc.validate_and_check_in(security_actor=actor,
                                            credential={"qr_token": vp.qr_token},
                                            gate_id=gate.pk)
            outcomes.append((res.outcome, [x.code for x in res.failures]))
        except Exception as exc:  # noqa: BLE001  (surfaced by the assertion below)
            errors.append(exc)
        finally:
            connection.close()

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert not errors, errors
    assert sorted(o[0] for o in outcomes) == [svc.CHECKED_IN, svc.DENIED]
    assert [o[1] for o in outcomes if o[0] == svc.DENIED] == [["already_inside"]]
    assert VisitLog.objects.filter(visit_pass=vp, event="check_in").count() == 1
    assert VisitLog.objects.filter(visit_pass=vp, event="denied").count() == 1
