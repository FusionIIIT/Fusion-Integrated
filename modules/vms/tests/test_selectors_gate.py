"""Read-side gate selectors: who is alerted, which gates a user may see, denial and alert
filters, the offline roster and elevations (CFR-013, CFR-014, CFR-025, CFR-026)."""
from datetime import timedelta

import pytest
from django.utils import timezone

from modules.vms.models import Alert, RoleAssignment, VisitLog
from modules.vms.selectors import gate as sel
from modules.vms.tests import factories as f

pytestmark = pytest.mark.django_db
SCOPE = RoleAssignment.ScopeType
ROLE = RoleAssignment.Role


@pytest.fixture
def two_gates():
    z1, z2 = f.make_zone(), f.make_zone()
    return f.make_gate(zone=z1), f.make_gate(zone=z2)


# --- alert_recipients ---------------------------------------------------------------------

def test_alert_recipients_without_a_gate_are_admins_and_campus_security():
    f.make_role_assignment(user_id=1, role=ROLE.ADMIN, scope_type=SCOPE.CAMPUS)
    f.make_role_assignment(user_id=2, role=ROLE.SECURITY, scope_type=SCOPE.CAMPUS)
    f.make_role_assignment(user_id=3, role=ROLE.SECURITY, scope_type=SCOPE.GATE, scope_id=999)
    assert sel.alert_recipients(None) == [1, 2]


def test_alert_recipients_include_security_of_that_gate_and_its_zone(two_gates):
    g1, g2 = two_gates
    f.make_role_assignment(user_id=10, role=ROLE.SECURITY, scope_type=SCOPE.GATE,
                           scope_id=g1.pk)
    f.make_role_assignment(user_id=11, role=ROLE.SECURITY, scope_type=SCOPE.ZONE,
                           scope_id=g1.zone_id)
    f.make_role_assignment(user_id=12, role=ROLE.SECURITY, scope_type=SCOPE.GATE,
                           scope_id=g2.pk)
    assert sel.alert_recipients(g1.pk) == [10, 11]


def test_alert_recipients_skip_revoked_future_and_expired_assignments():
    now = timezone.now()
    f.make_role_assignment(user_id=20, role=ROLE.ADMIN, revoked_at=now)
    f.make_role_assignment(user_id=21, role=ROLE.ADMIN, starts_at=now + timedelta(days=1),
                           ends_at=now + timedelta(days=2))
    f.make_role_assignment(user_id=22, role=ROLE.ADMIN, starts_at=now - timedelta(days=2),
                           ends_at=now - timedelta(days=1))
    f.make_role_assignment(user_id=23, role=ROLE.ADMIN)
    assert sel.alert_recipients(None) == [23]


def test_alert_recipients_for_a_gate_that_does_not_exist_fall_back_to_campus_scope():
    f.make_role_assignment(user_id=30, role=ROLE.SECURITY, scope_type=SCOPE.CAMPUS)
    assert sel.alert_recipients(987654) == [30]


# --- gate_scope ---------------------------------------------------------------------------

def test_gate_scope_of_a_user_with_no_role_is_empty():
    assert sel.gate_scope(404) == set()


def test_gate_scope_campus_means_every_gate():
    f.make_role_assignment(user_id=40, scope_type=SCOPE.CAMPUS)
    assert sel.gate_scope(40) is None


def test_gate_scope_gate_and_zone_assignments_combine(two_gates):
    g1, g2 = two_gates
    extra = f.make_gate(zone=g1.zone)
    f.make_role_assignment(user_id=41, scope_type=SCOPE.GATE, scope_id=g2.pk)
    f.make_role_assignment(user_id=41, scope_type=SCOPE.ZONE, scope_id=g1.zone_id)
    assert sel.gate_scope(41) == {g1.pk, extra.pk, g2.pk}


# --- denials and alerts -----------------------------------------------------------------

@pytest.fixture
def denials(two_gates):
    g1, g2 = two_gates
    open_, overridden, escalated, other = (
        f.make_visit_log(event=VisitLog.Event.DENIED, gate=g1),
        f.make_visit_log(event=VisitLog.Event.DENIED, gate=g1),
        f.make_visit_log(event=VisitLog.Event.DENIED, gate=g1),
        f.make_visit_log(event=VisitLog.Event.DENIED, gate=g2))
    f.make_gate_override(visit_log=overridden)
    f.make_escalation(visit_log=escalated)
    return g1, g2, open_, overridden, escalated, other


def _ids(qs):
    return {r.pk for r in qs}


def _mine(qs, denials):
    """Only the denials this test made: the override/escalation factories add stray logs."""
    return _ids(qs) & {d.pk for d in denials[2:]}


def test_denials_filter_by_status_for_a_campus_user(denials):
    _, _, open_, overridden, escalated, other = denials
    f.make_role_assignment(user_id=50, scope_type=SCOPE.CAMPUS)
    assert _mine(sel.denials(50), denials) == {open_.pk, escalated.pk, other.pk}
    assert _mine(sel.denials(50, "overridden"), denials) == {overridden.pk}
    assert _mine(sel.denials(50, "escalated"), denials) == {escalated.pk}
    assert _mine(sel.denials(50, "all"), denials) == {
        open_.pk, overridden.pk, escalated.pk, other.pk}


def test_denials_are_limited_to_the_gates_of_a_scoped_user(denials):
    g1, _, open_, overridden, escalated, _ = denials
    f.make_role_assignment(user_id=51, scope_type=SCOPE.GATE, scope_id=g1.pk)
    assert _mine(sel.denials(51, "all"), denials) == {open_.pk, overridden.pk, escalated.pk}
    assert _ids(sel.denials(404, "all")) == set()


def test_alerts_filter_by_status_and_kind_within_scope(two_gates):
    g1, g2 = two_gates
    a = f.make_alert(kind=Alert.Kind.SUSPICIOUS, detail={"gate_id": g1.pk})
    b = f.make_alert(kind=Alert.Kind.BLACKLIST_HIT, detail={"gate_id": g1.pk},
                     status=Alert.Status.HANDLED)
    c = f.make_alert(kind=Alert.Kind.SUSPICIOUS, detail={"gate_id": g2.pk})
    f.make_role_assignment(user_id=60, scope_type=SCOPE.CAMPUS)
    f.make_role_assignment(user_id=61, scope_type=SCOPE.GATE, scope_id=g1.pk)
    assert _ids(sel.alerts(60)) == {a.pk, b.pk, c.pk}
    assert _ids(sel.alerts(60, status="handled")) == {b.pk}
    assert _ids(sel.alerts(60, kind="suspicious")) == {a.pk, c.pk}
    assert _ids(sel.alerts(61)) == {a.pk, b.pk}
    assert _ids(sel.alerts(61, status="open", kind="suspicious")) == {a.pk}


# --- offline roster and elevations --------------------------------------------------------

def test_cached_roster_has_digests_initials_and_zones_but_no_raw_credentials():
    vr = f.make_visit_request(status="approved", visitor=f.make_visitor(full_name="ravi kumar"))
    zone = f.make_zone()
    vp = f.make_visit_pass(visit_request=vr)
    vp.allowed_zones.add(zone)
    rows = sel.cached_roster(1)
    assert len(rows) == 1
    row = rows[0]
    assert row["initials"] == "RK" and row["zone_ids"] == [zone.pk]
    assert row["qr_sha256"] != vp.qr_token and len(row["qr_sha256"]) == 64
    assert vp.qr_token not in str(row) and vp.otp not in str(row)


def test_cached_roster_leaves_out_inactive_terminated_expired_and_unapproved_passes():
    now = timezone.now()
    f.make_visit_pass(visit_request=f.make_visit_request(status="approved"), is_active=False)
    f.make_visit_pass(visit_request=f.make_visit_request(status="approved"), terminated_at=now)
    f.make_visit_pass(visit_request=f.make_visit_request(status="approved"),
                      valid_until=now - timedelta(minutes=1))
    f.make_visit_pass(visit_request=f.make_visit_request(status="pending"))
    assert sel.cached_roster(1) == []


def test_elevations_filter_by_pass_and_by_whether_they_are_active_now():
    vp = f.make_visit_pass()
    now = timezone.now()
    live = f.make_zone_elevation(visit_pass=vp, starts_at=now - timedelta(minutes=5),
                                 ends_at=now + timedelta(minutes=5))
    past = f.make_zone_elevation(visit_pass=vp, starts_at=now - timedelta(hours=2),
                                 ends_at=now - timedelta(hours=1))
    revoked = f.make_zone_elevation(visit_pass=vp, starts_at=now - timedelta(minutes=5),
                                    ends_at=now + timedelta(minutes=5), revoked_at=now)
    other = f.make_zone_elevation()
    assert _ids(sel.elevations(pass_id=vp.pk)) == {live.pk, past.pk, revoked.pk}
    assert _ids(sel.elevations(pass_id=vp.pk, active_only=True)) == {live.pk}
    assert other.pk in _ids(sel.elevations())
