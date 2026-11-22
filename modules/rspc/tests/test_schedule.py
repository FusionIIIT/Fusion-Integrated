"""Tests for RSPC Celery beat schedule and scheduled tasks."""

import datetime

import pytest

from modules.rspc.schedule import SCHEDULE
from modules.rspc.services import project as project_services
from modules.rspc.tasks import check_project_deadlines


def test_schedule_definition_is_valid():
    """Verify Celery beat configuration contains expected deadlines check."""
    assert "rspc-check-project-deadlines" in SCHEDULE
    entry = SCHEDULE["rspc-check-project-deadlines"]
    assert entry["task"] == "modules.rspc.tasks.check_project_deadlines"
    assert entry["schedule"] == 86400.0


@pytest.mark.django_db
def test_check_project_deadlines_task():
    today = datetime.date.today()
    past = today - datetime.timedelta(days=10)
    future = today + datetime.timedelta(days=100)

    # Sanction expired project
    p1 = project_services.sanction_and_register_project(
        user_id=1,
        project_code="RSPC/TEST/001",
        project_type="sponsored",
        title="Expired Grant",
        department="CSE",
        funding_agency="DST",
        sanction_order_no="DST/01",
        sanction_date=past,
        start_date=past,
        end_date=past,
        sanctioned_amount=100000.0,
    )
    project_services.activate_project(project=p1, actor_role="admin")

    # Sanction future project
    p2 = project_services.sanction_and_register_project(
        user_id=2,
        project_code="RSPC/TEST/002",
        project_type="sponsored",
        title="Active Grant",
        department="CSE",
        funding_agency="DST",
        sanction_order_no="DST/02",
        sanction_date=today,
        start_date=today,
        end_date=future,
        sanctioned_amount=200000.0,
    )
    project_services.activate_project(project=p2, actor_role="admin")

    # Run scheduled task
    expired_count = check_project_deadlines()
    assert expired_count == 1
