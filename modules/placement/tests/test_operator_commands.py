"""Operator commands and scheduled tasks, each run once and its effect observed."""
from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from modules.placement import contracts, tasks
from modules.placement.models import (
    Application,
    NotificationOutbox,
    Offer,
    PlacementStatsSnapshot,
)
from modules.placement.services import notifications
from modules.placement.tests.test_spec_journeys import SEASON, STUDENT, World

pytestmark = pytest.mark.django_db


def _queue(n=1, **kw):
    for i in range(n):
        notifications.enqueue(topic="offer.issued", dedupe_key=f"k{i}", subject="s",
                              body="b", recipient_email=f"s{i}@example.test", **kw)


def _run(*args):
    out = StringIO()
    call_command("send_notifications", *args, stdout=out)
    return out.getvalue()


def test_send_notifications_drains_the_queue(mailoutbox):
    # PC-BR-021, PC-AFR-057
    _queue(2)
    assert "queue drained" in _run()
    assert len(mailoutbox) == 2
    assert set(NotificationOutbox.objects.values_list("status", flat=True)) == {"sent"}


def test_send_notifications_reports_what_is_left_under_a_limit(mailoutbox):
    _queue(3)
    assert "still pending" in _run("--limit", "1")
    assert len(mailoutbox) == 1


def test_status_reports_counts_and_recent_failures():
    _queue(1)
    NotificationOutbox.objects.update(status="failed", last_error="smtp down")
    out = _run("--status")
    assert "failed" in out
    assert "smtp down" in out


def test_retry_failed_requeues_parked_rows():
    _queue(1)
    NotificationOutbox.objects.update(status="failed", attempts=5)
    assert "Re-queued 1" in _run("--retry-failed")
    assert NotificationOutbox.objects.get().status == "pending"


def test_deliver_task_sends(mailoutbox):
    _queue(1)
    assert "sent=1" in tasks.deliver_notifications()


def test_expiry_task_closes_an_overdue_offer(stub_iam):
    # PC-BR-013
    world = World(stub_iam)
    app = world.student_applies(world.company_publishes())
    world.company_shortlists(app)
    offer = world.company_offers(app)
    Offer.objects.filter(pk=offer).update(respond_by=timezone.now() - timedelta(minutes=1))
    assert tasks.expire_overdue_offers() == 1
    assert Offer.objects.get(pk=offer).status == "expired"
    assert Application.objects.get(pk=app).status == "offer_expired"


def test_stats_task_rebuilds_every_active_season(stub_iam):
    World(stub_iam)
    assert tasks.rebuild_active_stats() >= 1
    assert PlacementStatsSnapshot.objects.filter(policy__season=SEASON).exists()


def test_placement_status_contract_is_plural_and_counts_acceptances(stub_iam):
    world = World(stub_iam)
    app = world.student_applies(world.company_publishes())
    world.company_shortlists(app)
    world.student_responds(world.company_offers(app), accept=True)
    status = contracts.get_placement_status([STUDENT, 4242, None], SEASON)
    assert (status[STUDENT].is_placed, status[STUDENT].accepted_count) == (True, 1)
    assert status[4242].is_placed is False
    assert contracts.get_placement_status([], SEASON) == {}


def test_open_placement_season_creates_it_once_with_the_signed_categories():
    # PC-BR-013, PC-BR-015: the deadline and the multiple-offer policy are represented.
    from modules.placement.models import PlacementPolicy
    out = StringIO()
    call_command("open_placement_season", "--season", "2030-31",
                 "--registration-closes", "2030-08-31", "--offer-hours", "48", stdout=out)
    policy = PlacementPolicy.objects.get(season="2030-31")
    assert policy.default_offer_response_hours == 48
    assert policy.categories.count() > 0
    call_command("open_placement_season", "--season", "2030-31", "--offer-hours", "1",
                 stdout=out)
    assert "nothing changed" in out.getvalue()
    policy.refresh_from_db()
    assert policy.default_offer_response_hours == 48


@pytest.mark.parametrize("args", [["--season", " "], ["--season", "2031-32", "--offer-hours", "0"]])
def test_open_placement_season_refuses_bad_input(args):
    from django.core.management.base import CommandError
    with pytest.raises(CommandError):
        call_command("open_placement_season", *args, stdout=StringIO())


def test_readiness_names_the_missing_season_until_one_is_opened():
    # PC-BR-013, PC-BR-015: no season means no deadline and no offer policy to apply.
    from modules.placement import registry
    assert "open_placement_season" in registry.readiness()[0]
    call_command("open_placement_season", "--season", "2032-33", stdout=StringIO())
    assert registry.readiness() == []


def test_placement_readiness_command_prints_the_same_list():
    from django.core.management.base import CommandError
    out = StringIO()
    with pytest.raises(CommandError):
        call_command("placement_readiness", stdout=out)
    assert "open_placement_season" in out.getvalue()
    call_command("open_placement_season", "--season", "2033-34", stdout=StringIO())
    call_command("placement_readiness", stdout=out)
    assert "ready" in out.getvalue()
