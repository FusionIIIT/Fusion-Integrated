"""The SLA runner as an operator sees it."""
from datetime import date, timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from modules.leave.domain.categories import Category
from modules.leave.domain.state_machine import State
from modules.leave.models import LeaveRequest, SlaClock, SlaRule
from modules.leave.tests import factories

pytestmark = pytest.mark.django_db


@pytest.fixture
def overdue():
    policy = factories.make_policy()
    SlaRule.objects.create(
        policy_id=policy.pk, state=State.AWAITING_UNIT_HEAD.value,
        remind_after_hours=48, escalate_after_hours=96)
    request = LeaveRequest.objects.create(
        user_id=501, category=Category.CL.value,
        state=State.AWAITING_UNIT_HEAD.value,
        starts_on=date(2026, 3, 2), ends_on=date(2026, 3, 3), reason="Personal",
        requested_days=2, policy_id=policy.pk, unit="CSE")
    started = timezone.now() - timedelta(hours=100)
    return SlaClock.objects.create(
        request=request, state=State.AWAITING_UNIT_HEAD.value, started_at=started,
        remind_at=started + timedelta(hours=48),
        escalate_at=started + timedelta(hours=96))


def run(*args) -> str:
    out = StringIO()
    call_command("leave_sla", *args, stdout=out)
    return out.getvalue()


def test_it_reminds_and_escalates_what_is_overdue(overdue):
    output = run()

    assert "reminded   1" in output
    assert "escalated  1" in output
    assert "passed their deadline" in output


def test_a_second_pass_changes_nothing(overdue):
    run()

    output = run()

    assert "reminded   0" in output
    assert "nothing overdue" in output


def test_status_reports_without_sending(overdue):
    output = run("--status")

    assert f"request {overdue.request_id}" in output
    overdue.refresh_from_db()
    assert overdue.reminded_at is None


def test_status_says_so_when_there_is_nothing_to_chase():
    assert "no open clocks" in run("--status")
