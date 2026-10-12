"""SLA reminders and escalations (BR-EL-032…034)."""
from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from modules.leave.models import LeaveNotification, SlaThreshold
from modules.leave.services import sla
from modules.leave.tests.conftest import (
    APPLICANT,
    DEAN,
    SELF,
    SUBSTITUTE,
    UH,
    UNIT_HEAD,
)

pytestmark = pytest.mark.django_db


def _pending_file(client, **overrides):
    payload = {"category": "el", "start_date": "2026-10-26",
               "end_date": "2026-10-28",
               "substitute_user_id": SUBSTITUTE}
    payload.update(overrides)
    c = client(APPLICANT, permissions=SELF)
    return c.post("/api/v1/leave/requests", payload, format="json").json()


def test_reminder_fires_once_then_escalation(stub_iam, desks, client):
    pk = _pending_file(client)["id"]
    now = timezone.now()

    # 25h in: the reminder threshold (24h) has passed, escalation (48h) has not.
    result = sla.sweep(now=now + timedelta(hours=25))
    assert result == {"reminded": 1, "escalated": 0}
    # CFR-EL-031: the responsible user — the substitute holding the task.
    assert LeaveNotification.objects.filter(
        user_id=SUBSTITUTE, kind="sla_reminder").exists()

    # A second sweep at the same instant must not double-notify.
    assert sla.sweep(now=now + timedelta(hours=25))["reminded"] == 0

    # 50h in: escalation, and BR-EL-033 re-routes the file to the
    # configured higher authority (DEAN on the seeded threshold).
    result = sla.sweep(now=now + timedelta(hours=50))
    assert result["escalated"] == 1
    assert LeaveNotification.objects.filter(
        user_id=DEAN, kind="sla_escalation").exists()
    from modules.leave.models import LeaveRequest
    request = LeaveRequest.objects.get(pk=pk)
    assert request.task_user_id == DEAN
    assert request.escalated_at is not None


def test_terminal_files_are_never_swept(stub_iam, desks, client):
    pk = _pending_file(client)["id"]
    client(SUBSTITUTE, permissions=SELF).post(
        f"/api/v1/leave/requests/{pk}/substitute/respond",
        {"response": "accept"}, format="json")
    # Now on the Unit Head's desk with a fresh clock; the substitute's
    # closed task must not re-fire anything.
    result = sla.sweep(now=timezone.now() + timedelta(hours=1))
    assert result == {"reminded": 0, "escalated": 0}


def test_unconfigured_task_class_is_skipped(stub_iam, desks, client):
    SlaThreshold.objects.all().delete()
    _pending_file(client)
    assert sla.sweep(now=timezone.now() + timedelta(days=30)) == {
        "reminded": 0, "escalated": 0}
