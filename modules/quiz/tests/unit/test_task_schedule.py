"""Non-database checks for Quiz Celery registration and beat configuration."""

from config.celery import app
from modules.quiz import tasks as quiz_tasks
from modules.quiz.schedule import BEAT_SCHEDULE, TASK_ROUTES


def test_quiz_periodic_tasks_are_registered_and_routed() -> None:
    expected = {
        "quiz.tasks.auto_submit_expired_attempts",
        "quiz.tasks.process_quiz_boundaries",
    }
    assert {entry["task"] for entry in BEAT_SCHEDULE.values()} == expected
    assert expected <= set(app.tasks)
    assert expected == set(TASK_ROUTES)
    assert all(route["queue"] == "default" for route in TASK_ROUTES.values())
    assert quiz_tasks.auto_submit_expired_attempts.name in expected
    assert quiz_tasks.process_quiz_boundaries.name in expected


def test_quiz_beat_entries_have_stale_work_expiries() -> None:
    assert all(entry["schedule"] == 15.0 for entry in BEAT_SCHEDULE.values())
    assert all(entry["options"]["expires"] == 14 for entry in BEAT_SCHEDULE.values())
    assert all(entry["options"]["queue"] == "default" for entry in BEAT_SCHEDULE.values())
