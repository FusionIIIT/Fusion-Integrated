"""The command that makes "beat is not running" visible.

Nothing errors when beat stops; work just stops. These are the two symptoms.
"""
from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from modules.placement.models import (
    Application,
    Company,
    JobPosting,
    NotificationOutbox,
    Offer,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def posting():
    company = Company.objects.create(
        name="Acme", slug="acme", status="active",
        approval_status="approved", approved_by_user_id=9)
    return JobPosting.objects.create(
        company=company, placement_year="2026-27", title="SDE",
        description="Build things.", status="published",
        closes_at=timezone.now() + timedelta(days=7),
        eligibility_rule={"gte": ["cpi", 7.0]},
        eligibility_rule_locked_at=timezone.now())


def _run(*args):
    out = StringIO()
    try:
        call_command("scheduled_work_status", *args, stdout=out)
    except SystemExit as exc:
        return out.getvalue(), exc.code
    return out.getvalue(), 0


def test_a_quiet_system_is_healthy():
    out, code = _run()
    assert code == 0
    assert "healthy" in out


def test_an_offer_past_its_deadline_is_reported(posting):
    """It still blocks the student's pool until the sweep retires it, which is
    what makes a stopped beat cost someone their place."""
    application = Application.objects.create(
        posting=posting, user_id=1001, status="selected", cpi_at_apply="8.00")
    Offer.objects.create(posting=posting, application=application,
                         user_id=1001, ctc_lpa="12.00", status="issued",
                         respond_by=timezone.now() - timedelta(days=2))
    out, code = _run()
    assert code == 1
    assert "past respond_by" in out


def test_outbox_lag_beyond_the_threshold_is_reported():
    row = NotificationOutbox.objects.create(topic="posting.published",
                                            recipient_email="a@b.test",
                                            status="pending", payload={})
    NotificationOutbox.objects.filter(pk=row.pk).update(
        created_at=timezone.now() - timedelta(hours=2))

    out, code = _run("--max-lag", "600")
    assert code == 1
    assert "outbox lag" in out

    # Without a threshold it reports but does not fail: a backlog is only a
    # problem relative to how long it has been there.
    _, code = _run()
    assert code == 0
