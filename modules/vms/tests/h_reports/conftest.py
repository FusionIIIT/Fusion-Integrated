"""Fixed dataset for lane H. Every report test asserts exact numbers from it.

Local time is Asia/Kolkata (settings). D1=2026-03-10 (Tue), D2=2026-03-11, D3=2026-03-16
(Monday of the next week), plus one request on 2026-02-20.

Policy P1 (approval timeout 4h) is published 2026-01-01; P2 (2h) on D2 00:00.

Requests (created -> decided delta), host / visitor / zone / policy:
  D1  r1 09:00 +1h30 approved   h2001 V1 Z1 P1      r2 09:30 +4h00 approved   h2001 V2 Z1
      r3 10:00 +5h   completed  h2001 V1 Z2         r4 10:30 +0h30 rejected   h2002 V3 Z2
      r5 11:00 expired          h2002 V3 Z2         r6 11:30 pending          h2003 V4 Z1
      r7 14:00 +4h01 approved   h2002 V1 Z1
  D2  r8 09:00 +1h59 approved   h2001 V1 Z1 P2      r9 09:00 +2h00 approved   h2001 V2 Z1
      r10 10:00 +3h approved    h2003 V5 Z2         r11 10:30 +0h20 rejected  h2003 V5 Z2
      r12 12:00 +13h completed  h2002 V1 Z1         r13 15:00 expired         h2002 V4 Z2
  D3  r14 09:00 +1h approved    h2001 V1 Z1         r15 09:00 +25h approved   h2001 V1 Z1
  Feb r16 02-20 10:00 +1h approved h2001 V2 Z1 (P1)
Gate GA is in Z1, GB in Z2.
"""
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from django.utils import timezone

from modules.vms.models import GateOverride, RoleAssignment
from modules.vms.tests import factories as f

VIEW = "vms.report.view"
EXPORT = "vms.report.export"
PII = "vms.report.view_pii"


def at(day, hour=0, minute=0):
    """Aware local time; `day` is 'YYYY-MM-DD'."""
    y, m, d = map(int, day.split("-"))
    return timezone.make_aware(datetime(y, m, d, hour, minute))


HOUR, MIN = timedelta(hours=1), timedelta(minutes=1)
D1, D2, D3, FEB = "2026-03-10", "2026-03-11", "2026-03-16", "2026-02-20"


@pytest.fixture
def reporter():
    """Report viewer with no admin assignment: sees every zone."""
    return f.make_actor(permissions=[VIEW, EXPORT], user_id=4000)


@pytest.fixture
def pii_reporter():
    return f.make_actor(permissions=[VIEW, EXPORT, PII], user_id=4002)


@pytest.fixture
def zone_admin(data):
    """Admin whose assignment covers Z1 only."""
    f.make_role_assignment(user_id=4001, role=RoleAssignment.Role.ADMIN,
                           scope_type=RoleAssignment.ScopeType.ZONE, scope_id=data.z1.pk)
    return f.make_actor(permissions=[VIEW, EXPORT], user_id=4001)


@pytest.fixture(autouse=True)
def departments(monkeypatch):
    """Directory stub: host 2001 -> CS, 2002 -> EE, 2003 unknown."""
    from modules.vms.services import reports

    people = {2001: SimpleNamespace(department="CS"), 2002: SimpleNamespace(department="EE")}
    monkeypatch.setattr(reports, "_directory_users",
                        lambda ids: {i: people[i] for i in ids if i in people})


@pytest.fixture
def data(db):
    d = SimpleNamespace()
    d.z1 = f.make_zone(name="Z1", is_restricted=True)
    d.z2 = f.make_zone(name="Z2")
    d.ga = f.make_gate(name="Gate A", zone=d.z1)
    d.gb = f.make_gate(name="Gate B", zone=d.z2)
    f.make_published_policy(version=1, published_at=at("2026-01-01"),
                            approval_timeout_hours=4)
    f.make_published_policy(version=2, published_at=at(D2), approval_timeout_hours=2)
    d.v = {n: f.make_visitor(full_name=f"Person {n}", phone=f"98000000{n}{n}",
                             email=f"p{n}@corp.example", id_doc_number=f"PASS-{n}{n}{n}")
           for n in range(1, 6)}
    d.r, d.p = {}, {}

    def req(n, day, hh, mm, host, vis, status, zone, decided=None):
        created = at(day, hh, mm)
        r = f.make_visit_request(
            visitor=d.v[vis], host_user_id=host, status=status,
            decided_at=(created + decided) if decided is not None else None,
            decision_note="note" if decided is not None else "")
        type(r).objects.filter(pk=r.pk).update(created_at=created)
        r.requested_zones.add(zone)
        d.r[n] = r
        d.p[n] = f.make_visit_pass(visit_request=r)

    req(1, D1, 9, 0, 2001, 1, "approved", d.z1, 90 * MIN)
    req(2, D1, 9, 30, 2001, 2, "approved", d.z1, 4 * HOUR)
    req(3, D1, 10, 0, 2001, 1, "completed", d.z2, 5 * HOUR)
    req(4, D1, 10, 30, 2002, 3, "rejected", d.z2, 30 * MIN)
    req(5, D1, 11, 0, 2002, 3, "expired", d.z2)
    req(6, D1, 11, 30, 2003, 4, "pending", d.z1)
    req(7, D1, 14, 0, 2002, 1, "approved", d.z1, 4 * HOUR + MIN)
    req(8, D2, 9, 0, 2001, 1, "approved", d.z1, 119 * MIN)
    req(9, D2, 9, 0, 2001, 2, "approved", d.z1, 2 * HOUR)
    req(10, D2, 10, 0, 2003, 5, "approved", d.z2, 3 * HOUR)
    req(11, D2, 10, 30, 2003, 5, "rejected", d.z2, 20 * MIN)
    req(12, D2, 12, 0, 2002, 1, "completed", d.z1, 13 * HOUR)
    req(13, D2, 15, 0, 2002, 4, "expired", d.z2)
    req(14, D3, 9, 0, 2001, 1, "approved", d.z1, HOUR)
    req(15, D3, 9, 0, 2001, 1, "approved", d.z1, 25 * HOUR)
    req(16, FEB, 10, 0, 2001, 2, "approved", d.z1, HOUR)

    def log(n, event, day, hh, mm, gate=None, zone=None, reason=""):
        return f.make_visit_log(visit_pass=d.p[n], event=event, gate=gate, zone=zone,
                                reason=reason, occurred_at=at(day, hh, mm))

    ci, co, auto = "check_in", "check_out", "auto_check_out"
    for n, day, hh, mm in [(1, D1, 9, 0), (2, D1, 9, 30), (3, D1, 10, 0), (7, D1, 14, 0),
                           (8, D2, 9, 30), (9, D2, 9, 45), (10, D2, 10, 5),
                           (14, D3, 9, 10)]:
        log(n, ci, day, hh, mm, gate=d.ga)
    log(1, co, D1, 12, 0, gate=d.ga)
    log(2, co, D1, 13, 0, gate=d.ga)
    log(3, auto, D1, 18, 0, gate=d.ga)
    log(8, co, D2, 12, 0, gate=d.ga)
    log(1, "denied", D1, 8, 0, gate=d.ga, reason="pass_inactive")
    log(2, "denied", D1, 8, 30, gate=d.ga, reason="outside_validity,zone_not_permitted")
    log(7, "denied", D1, 17, 0, gate=d.gb, reason="blacklisted")
    d.denied_v5 = log(10, "denied", D2, 8, 0, gate=d.ga, reason="pass_inactive")
    for ev, z, day, hh, k in [("zone_allowed", d.z1, D1, 9, 3), ("zone_denied", d.z1, D1, 9, 1),
                              ("zone_allowed", d.z2, D1, 10, 1), ("zone_denied", d.z2, D1, 10, 2),
                              ("zone_allowed", d.z1, D2, 9, 1), ("zone_allowed", d.z1, D3, 9, 1)]:
        for i in range(k):
            log(1, ev, day, hh, i, zone=z)

    ovr = GateOverride.objects.create(visit_log=d.denied_v5, admin_user_id=5001,
                                      justification="VIP guest")
    GateOverride.objects.filter(pk=ovr.pk).update(created_at=at(D2, 13, 10))

    def alert(kind, severity, day, hh, **detail):
        a = f.make_alert(kind=kind, severity=severity, detail=detail)
        type(a).objects.filter(pk=a.pk).update(created_at=at(day, hh))

    for day, hh, z in [(D1, 9, d.z1), (D1, 10, d.z2), (D1, 11, d.z2), (D2, 9, d.z2)]:
        alert("zone_violation", "high", day, hh, zone_id=z.pk, gate_id=None)
    alert("blacklist_hit", "high", D1, 9, checkpoint="pre_registration", visitor="Mallory")
    alert("blacklist_hit", "critical", D1, 10, checkpoint="walk_in", visitor="Trudy")
    alert("blacklist_hit", "high", D2, 9, gate_id=d.ga.pk)
    alert("blacklist_hit", "high", D2, 10, checkpoint="pre_registration")
    alert("blacklist_hit", "low", D3, 9, gate_id=d.ga.pk)
    return d
