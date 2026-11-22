"""Operator commands: venue seeding, readiness, a manual drain (deployment order, Step 7.5)."""
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from modules.gymkhana import registry
from modules.gymkhana.models import Venue, VenueList
from modules.gymkhana.selectors.venues import current_venue_names

pytestmark = pytest.mark.django_db


def test_readiness_names_the_missing_venue_list_then_passes():
    assert len(registry.readiness()) == 1
    assert "seed_gymkhana_venues" in registry.readiness()[0]
    with pytest.raises(CommandError):
        call_command("gymkhana_readiness", stderr=StringIO())
    call_command("seed_gymkhana_venues", "--venue", "LHTC 101", "--venue", " lhtc  101 ",
                 "--venue", "Open Air Theatre", stdout=StringIO())
    assert registry.readiness() == []
    out = StringIO()
    call_command("gymkhana_readiness", stdout=out)
    assert "ready" in out.getvalue()
    assert current_venue_names() == ["LHTC 101", "Open Air Theatre"]


def test_br_gym_020_a_new_list_supersedes_and_the_old_one_is_kept():
    call_command("seed_gymkhana_venues", "--venue", "A", "--effective-from", "2020-01-01",
                 stdout=StringIO())
    call_command("seed_gymkhana_venues", "--venue", "B", "--effective-from", "2021-01-01",
                 stdout=StringIO())
    call_command("seed_gymkhana_venues", "--venue", "C", "--effective-from", "2099-01-01",
                 stdout=StringIO())
    assert current_venue_names() == ["B"]
    assert VenueList.objects.count() == 3 and Venue.objects.count() == 3


@pytest.mark.parametrize("args,message", [
    ([], "at least one"),
    (["--venue", " "], "at least one"),
    (["--venue", "x" * 121], "at most"),
    (["--venue", "A", "--effective-from", "soon"], "2026-12-01"),
])
def test_seeding_refuses_bad_input_with_a_sentence(args, message):
    with pytest.raises(CommandError, match=message):
        call_command("seed_gymkhana_venues", *args, stdout=StringIO())


def test_the_same_effective_moment_twice_is_refused():
    call_command("seed_gymkhana_venues", "--venue", "A", "--effective-from", "2020-01-01",
                 stdout=StringIO())
    with pytest.raises(CommandError, match="already"):
        call_command("seed_gymkhana_venues", "--venue", "B", "--effective-from",
                     "2020-01-01", stdout=StringIO())


def test_manual_drain_prints_its_report(stub_iam):
    out = StringIO()
    call_command("gymkhana_deliver_notifications", "--limit", "5", stdout=out)
    assert out.getvalue().startswith("expanded=")


def test_model_labels_are_readable():
    from modules.gymkhana import models as m
    from modules.gymkhana.tests.conftest import make_club
    club = make_club()
    assert str(club) == "Robotics"
    from datetime import UTC, datetime
    venue_list = VenueList.objects.create(effective_from=datetime(2020, 1, 1, tzinfo=UTC),
                                          created_by_label="t")
    assert str(Venue(venue_list=venue_list, name="A")) == "A"
    assert str(venue_list).startswith("venues from 2020")
    assert str(m.VenueDay(venue_name="A", date="2026-01-01")) == "A 2026-01-01"
    assert str(m.PollTarget(batch_year=2023)) == "2023 all branches"
    assert str(m.PollChoice(label="x")) == "x"
    assert str(m.AuditEvent(action="a", object_type="club", object_id=1)) == "a club:1"
    assert "poll" in str(m.Vote(poll_id=1))
