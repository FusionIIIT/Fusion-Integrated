from datetime import timedelta

import pytest

from conftest import make_principal
from modules.elm.sla import process_sla
from modules.elm.tests.test_submission import pending_context
from modules.elm.workflows import substitute_response, withdraw

pytestmark = pytest.mark.django_db


def test_sla_reminder_is_once():
    req, _applicant, _authority, _leave_type = pending_context()
    task = req.events.get(action="TASK_ASSIGNED")
    now = task.created_at + timedelta(hours=23)
    assert process_sla(req.pk, now=now) == []
    now = task.created_at + timedelta(hours=25)
    assert process_sla(req.pk, now=now) == ["SLA_REMINDER"]
    now = task.created_at + timedelta(hours=26)
    assert process_sla(req.pk, now=now) == []
    assert req.events.get(action="SLA_REMINDER").details["recipient"] == 201
    assert not req.events.filter(action="SLA_ESCALATED").exists()


def test_sla_escalates_once_and_stops_after_withdrawal():
    req, applicant, _authority, _leave_type = pending_context(substitute=301)
    task = req.events.get(action="TASK_ASSIGNED")
    process_sla(req.pk, now=task.created_at + timedelta(hours=49))
    escalated = req.events.get(action="SLA_ESCALATED")
    assert escalated.details["recipient"] == 201
    process_sla(req.pk, now=task.created_at + timedelta(hours=50))
    withdraw(req.pk, applicant)
    assert req.events.filter(action__startswith="SLA_").count() == 2


def test_sla_skips_declined_and_withdrawn_requests():
    req, applicant, _, _ = pending_context(substitute=301)
    task = req.events.get(action="TASK_ASSIGNED")
    nominee = make_principal(
        user_id=301, kind="faculty", modules=("elm",), permissions=("elm.leave_requests.view",)
    )
    substitute_response(req.pk, nominee, False)

    # First assertion: process_sla returns empty list
    assert process_sla(req.pk, now=task.created_at + timedelta(hours=75)) == []

    # Check no SLA events exist
    assert not req.events.filter(action__startswith="SLA_").exists()

    # Withdraw the request
    withdraw(req.pk, applicant)

    # Repeat assertions after withdrawal
    assert process_sla(req.pk, now=task.created_at + timedelta(hours=75)) == []
    assert not req.events.filter(action__startswith="SLA_").exists()
