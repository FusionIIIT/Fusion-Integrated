"""Year-end and SLA, each run by hand once (SF-EL-001, SF-EL-002)."""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from fusion_auth.client import UserRef
from modules.directory import contracts as directory
from modules.elm.models import LeaveRequest, LedgerEntry, Notification, SlaAction
from modules.elm.services import sla, year_end

pytestmark = pytest.mark.django_db


def _credit(uid, cat, n, year=2025):
    LedgerEntry.objects.create(user_id=uid, category=cat, entry_type="annual_credit",
                               delta=n, year=year)


def _bal(uid, cat, year=None):
    qs = LedgerEntry.objects.filter(user_id=uid, category=cat)
    if year:
        qs = qs.filter(year=year)
    return sum(e.delta for e in qs)


def test_year_end_lapses_converts_carries_and_is_idempotent(stub_iam, policy):
    stub_iam(users={1: UserRef(1, "f", "F", "faculty"), 2: UserRef(2, "s", "S", "staff")})
    directory.get_users([1, 2])
    _credit(1, "CL", 8)
    _credit(1, "VL", 45)
    _credit(2, "EL", 30)
    _credit(2, "RH", 2)
    year_end.run(2025)
    year_end.run(2025)
    assert _bal(1, "VL", 2025) == 0
    assert _bal(1, "EL", 2025) == Decimal("22.50")
    assert _bal(1, "CL", 2025) == 0
    assert _bal(2, "EL", 2025) == 30
    assert _bal(2, "RH", 2025) == 0
    assert _bal(1, "VL") == 60
    assert _bal(2, "EL") == 60
    assert LedgerEntry.objects.filter(user_id=1, entry_type="lapse").count() == 1


def test_sla_reminds_once_and_skips_finished_tasks(policy):
    policy.hierarchy = {**policy.hierarchy, "sla": {
        "reminder_hours": 24, "escalation_hours": 72, "escalate_to": "Registrar"}}
    policy.save()
    old = timezone.now() - timedelta(hours=80)
    common = {"category": "CL", "applicant_kind": "faculty",
              "start_date": timezone.localdate(), "end_date": timezone.localdate(),
              "days": 1, "purpose": "x", "current_role": "HOD (CSE)",
              "route": [{"step": "unit_head", "role": "HOD (CSE)"}],
              "stage_entered_at": old}
    live = LeaveRequest.objects.create(user_id=1, status="awaiting_unit_head", **common)
    LeaveRequest.objects.create(user_id=2, status="approved", **common)
    assert sla.process() == {"reminders": 1, "escalations": 1}
    assert sla.process() == {"reminders": 0, "escalations": 0}
    assert SlaAction.objects.filter(request=live).count() == 2
    assert Notification.objects.filter(recipient_role="Registrar").count() == 1


def test_sla_is_off_until_thresholds_are_published(policy):
    assert sla.process() == {"reminders": 0, "escalations": 0}
