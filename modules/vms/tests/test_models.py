"""VMS Model Tests.
Tests database constraints, UUID/hash generation, and relations.
"""

from datetime import timedelta

import pytest
from django.utils import timezone

from modules.vms.models.access import GateAlert, GateLog
from modules.vms.models.muster import EmergencyMuster
from modules.vms.models.visitors import BlacklistEntry, Visitor
from modules.vms.models.visits import Visit

pytestmark = pytest.mark.django_db


def test_visitor_creation():
    v = Visitor.objects.create(
        first_name="Anita",
        last_name="Roy",
        email="anita.roy@example.com",
        phone="9876543210",
        id_type="aadhaar",
        id_number_hash="HASH_ANITA",
        organization="Research Lab",
    )
    assert v.id is not None
    assert v.is_active is True
    assert "Anita Roy" in str(v)


def test_visit_and_pass_lifecycle():
    visitor = Visitor.objects.create(
        first_name="Vikram",
        last_name="Patel",
        email="vikram@example.com",
        phone="9123456789",
        id_number_hash="HASH_VIKRAM",
    )
    now = timezone.now()
    visit = Visit.objects.create(
        visitor=visitor,
        host_user_id=101,
        purpose="Project Discussion",
        pass_number="PASS-20261122-0001",
        qr_code_hash="QR_HASH_0001",
        valid_from=now,
        valid_to=now + timedelta(hours=4),
        allowed_zones=["MAIN_GATE", "ADMIN_BLOCK"],
    )
    assert visit.id is not None
    assert visit.status == "requested"
    assert "PASS-20261122-0001" in str(visit)


def test_blacklist_record():
    bl = BlacklistEntry.objects.create(
        id_type="passport",
        id_number_hash="HASH_BANNED",
        full_name="Banned Guest",
        phone="9988776655",
        reason="Security breach attempt",
        severity="critical",
    )
    assert bl.id is not None
    assert bl.is_active is True
    assert "Banned Guest" in str(bl)


def test_gate_log_and_alert():
    visitor = Visitor.objects.create(
        first_name="Sunil",
        last_name="Verma",
        email="sunil@example.com",
        phone="9000000001",
        id_number_hash="HASH_SUNIL",
    )
    now = timezone.now()
    visit = Visit.objects.create(
        visitor=visitor,
        host_user_id=102,
        purpose="Vendor Audit",
        pass_number="PASS-SUNIL",
        qr_code_hash="QR-SUNIL",
        valid_from=now,
        valid_to=now + timedelta(hours=2),
    )

    glog = GateLog.objects.create(
        visit=visit,
        action="check_in",
        gate_name="Gate 1",
        logged_by=50,
    )
    assert glog.id is not None
    assert "GateLog check_in" in str(glog)

    alert = GateAlert.objects.create(
        alert_type="zone_violation",
        severity="warning",
        message="Unauthorized entry attempt",
        visit_id=visit.id,
    )
    assert alert.id is not None
    assert alert.status == "open"


def test_emergency_muster():
    muster = EmergencyMuster.objects.create(
        muster_code="MUSTER-TEST-001",
        status="active",
        triggered_by=1,
        headcount_total=15,
        headcount_accounted=10,
    )
    assert muster.id is not None
    assert muster.status == "active"
    assert "MUSTER-TEST-001" in str(muster)
