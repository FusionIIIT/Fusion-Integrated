"""Every timer names a real task, on a served queue, and running it by hand works."""
import pytest
from django.core.management import CommandError, call_command

from config.celery import app
from modules.gymkhana.schedule import BEAT_SCHEDULE, TASK_ROUTES
from modules.gymkhana.tasks import expire_polls
from modules.gymkhana.tests.support import make_club, make_poll, people


def test_every_entry_is_merged_and_names_a_registered_task():
    for name, entry in BEAT_SCHEDULE.items():
        assert app.conf.beat_schedule[name] == entry
        assert entry["task"] in app.tasks
        assert 0 < entry["options"]["expires"] < entry["schedule"]


def test_every_task_is_routed_to_a_served_queue():
    assert set(TASK_ROUTES) == {e["task"] for e in BEAT_SCHEDULE.values()}
    for task, route in TASK_ROUTES.items():
        assert app.conf.task_routes[task] == route
        assert route["queue"] in {"default", "notifications"}


@pytest.mark.django_db
def test_expiring_polls_twice_takes_effect_once():
    import datetime

    people()
    make_poll(make_club(), expires_in=-datetime.timedelta(minutes=1))
    assert [expire_polls(), expire_polls()] == [1, 0]


@pytest.mark.django_db
def test_the_operator_commands_run(capsys):
    call_command("gymkhana_run_tasks")
    call_command("gymkhana_readiness")
    assert "Gymkhana is ready." in capsys.readouterr().out


def test_readiness_says_what_is_missing(settings):
    settings.GYMKHANA_CONFIGURED_VENUES = []
    with pytest.raises(CommandError, match="GYMKHANA_CONFIGURED_VENUES"):
        call_command("gymkhana_readiness")
