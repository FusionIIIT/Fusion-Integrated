from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from modules.vms.domain import pass_rules as pr

NOW = datetime(2026, 1, 5, 10, 0, tzinfo=UTC)


@dataclass
class P:
    is_active: bool = True
    terminated: bool = False
    valid_from: datetime = NOW - timedelta(hours=1)
    valid_until: datetime = NOW + timedelta(hours=1)
    allowed_zone_ids: tuple = ()
    slot_start: datetime | None = None
    slot_end: datetime | None = None


@dataclass
class Pol:
    restricted_zone_ids: tuple = ()


def codes(fs):
    return [f.code for f in fs]


def test_clean_pass_has_no_failures():
    assert pr.validate_at_gate(P(), NOW, None) == []


def test_br_077_inactive_pass_denied():
    fs = pr.validate_at_gate(P(is_active=False), NOW, None)
    assert codes(fs) == [pr.PASS_INACTIVE] and fs[0].rule == "VMS-BR-077"


def test_br_190_outside_validity_both_edges():
    assert codes(pr.validate_at_gate(P(), NOW - timedelta(hours=2), None)) == [pr.OUTSIDE_VALIDITY]
    assert codes(pr.validate_at_gate(P(), NOW + timedelta(hours=2), None)) == [pr.OUTSIDE_VALIDITY]
    p = P()
    assert pr.validate_at_gate(p, p.valid_from, None) == []
    assert pr.validate_at_gate(p, p.valid_until, None) == []


def test_outside_slot():
    p = P(slot_start=NOW + timedelta(minutes=10), slot_end=NOW + timedelta(minutes=30))
    assert codes(pr.validate_at_gate(p, NOW, None)) == [pr.OUTSIDE_SLOT]
    assert pr.validate_at_gate(p, NOW + timedelta(minutes=20), None) == []


def test_blacklisted():
    assert codes(pr.validate_at_gate(P(), NOW, None, blacklisted=True)) == [pr.BLACKLISTED]


def test_br_191_zone_rules():
    assert codes(pr.validate_at_gate(P(allowed_zone_ids=(1,)), NOW, 2)) == [pr.ZONE_NOT_PERMITTED]
    assert pr.validate_at_gate(P(allowed_zone_ids=(1, 2)), NOW, 2) == []
    # empty allow-list = every non-restricted zone
    assert pr.validate_at_gate(P(), NOW, 5, Pol(restricted_zone_ids=(9,))) == []
    assert codes(pr.validate_at_gate(P(), NOW, 9, Pol(restricted_zone_ids=(9,)))) == [
        pr.ZONE_NOT_PERMITTED]
    assert pr.validate_at_gate(P(allowed_zone_ids=(9,)), NOW, 9, Pol(restricted_zone_ids=(9,))) == []


def test_already_inside():
    assert codes(pr.validate_at_gate(P(), NOW, None, open_checkin=True)) == [pr.ALREADY_INSIDE]


def test_terminated_reports_terminated_not_inactive():
    p = P(is_active=False, terminated=True)
    assert codes(pr.validate_at_gate(p, NOW, None)) == [pr.TERMINATED]


def test_returns_all_failures_in_rule_order():
    p = P(is_active=False, allowed_zone_ids=(1,), valid_until=NOW - timedelta(minutes=1),
          slot_start=NOW + timedelta(hours=1), slot_end=NOW + timedelta(hours=2))
    fs = pr.validate_at_gate(p, NOW, 2, blacklisted=True, open_checkin=True)
    assert codes(fs) == [pr.PASS_INACTIVE, pr.OUTSIDE_VALIDITY, pr.OUTSIDE_SLOT, pr.BLACKLISTED,
                         pr.ZONE_NOT_PERMITTED, pr.ALREADY_INSIDE]
    assert codes(fs) == sorted(codes(fs), key=pr.FAILURE_ORDER.index)
    t = P(terminated=True, is_active=False)
    assert codes(pr.validate_at_gate(t, NOW, None, blacklisted=True, open_checkin=True)) == [
        pr.BLACKLISTED, pr.ALREADY_INSIDE, pr.TERMINATED]


def test_d14_override_eligible_constant():
    assert {pr.PASS_INACTIVE, pr.OUTSIDE_VALIDITY,
                                    pr.ZONE_NOT_PERMITTED, pr.OUTSIDE_SLOT} == pr.OVERRIDE_ELIGIBLE
    assert pr.BLACKLISTED not in pr.OVERRIDE_ELIGIBLE and pr.TERMINATED not in pr.OVERRIDE_ELIGIBLE


def test_is_overridable():
    assert not pr.is_overridable([])
    assert pr.is_overridable(pr.validate_at_gate(P(is_active=False), NOW, None))
    assert not pr.is_overridable(pr.validate_at_gate(P(is_active=False), NOW, None, blacklisted=True))
    assert not pr.is_overridable(pr.validate_at_gate(P(terminated=True), NOW, None))
