"""Tests for Complaint Management System scheduled tasks and beat configuration."""
import pytest
from config.celery import app as celery_app
from modules.complaints import schedule
from modules.complaints import tasks


def test_schedule_defines_beat_and_routes():
    """Verify schedule module exports valid BEAT_SCHEDULE and TASK_ROUTES."""
    assert hasattr(schedule, "BEAT_SCHEDULE")
    assert hasattr(schedule, "TASK_ROUTES")

    assert "complaints.check-and-escalate-sla-breaches" in schedule.BEAT_SCHEDULE
    assert "complaints.check-and-send-sla-reminders" in schedule.BEAT_SCHEDULE

    escalate_entry = schedule.BEAT_SCHEDULE["complaints.check-and-escalate-sla-breaches"]
    assert escalate_entry["task"] == "complaints.check_and_escalate_sla_breaches"
    assert escalate_entry["schedule"] == 300.0

    remind_entry = schedule.BEAT_SCHEDULE["complaints.check-and-send-sla-reminders"]
    assert remind_entry["task"] == "complaints.check_and_send_sla_reminders"
    assert remind_entry["schedule"] == 900.0


def test_tasks_are_registered_with_celery():
    """Verify shared tasks are registered with Celery by their expected task names."""
    assert tasks.check_and_escalate_sla_breaches.name == "complaints.check_and_escalate_sla_breaches"
    assert tasks.check_and_send_sla_reminders.name == "complaints.check_and_send_sla_reminders"


def test_celery_app_merges_complaints_schedule():
    """Verify Celery app includes complaints tasks in beat_schedule and task_routes."""
    beat_schedule = celery_app.conf.beat_schedule
    task_routes = celery_app.conf.task_routes

    assert "complaints.check-and-escalate-sla-breaches" in beat_schedule
    assert "complaints.check-and-send-sla-reminders" in beat_schedule
    assert "complaints.check_and_escalate_sla_breaches" in task_routes
    assert "complaints.check_and_send_sla_reminders" in task_routes
