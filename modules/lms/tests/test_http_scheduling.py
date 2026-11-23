import time
from datetime import timedelta

import pytest
from celery.contrib.testing.worker import start_worker
from django.test import override_settings
from django.utils import timezone

from config.celery import app
from modules.lms.domain.rules import RuleViolation
from modules.lms.tests.conftest import draft

pytestmark = pytest.mark.django_db(transaction=True)
BASE = "/api/v1/lms"


@pytest.fixture
def release_worker():
    with (
        override_settings(
            CELERY_TASK_ALWAYS_EAGER=False,
            CELERY_BROKER_URL="memory://",
            CELERY_RESULT_BACKEND="cache+memory://",
        ),
        start_worker(app, perform_ping_check=False, pool="solo", shutdown_timeout=10),
    ):
        yield


def schedule(world, kind):
    if kind == "assignments":
        row = draft(world)
    else:
        response = world.actor().post(
            f"{BASE}/courses/{world.workspace.pk}/materials/",
            {"kind": "NOTE", "text": "Scheduled lesson"},
            format="json",
        )
        assert response.status_code == 201
        row = response.json()
    url = f"{BASE}/{kind}/{row['id']}/"
    at = timezone.now() + timedelta(seconds=1)
    response = world.actor().post(url + "publish/", {"release_at": at.isoformat()}, format="json")
    assert response.status_code == 200 and response.json()["state"] == "SCHEDULED"
    assert world.actor("student").get(url).status_code == 404
    return url


def eventually(read, predicate, timeout=8):
    deadline = time.monotonic() + timeout
    value = read()
    while not predicate(value) and time.monotonic() < deadline:
        time.sleep(0.1)
        value = read()
    assert predicate(value), value


def test_uc_lms_015_scheduled_material_and_assignment_release(world, release_worker):
    # Source obligations: AFR-LMS-003.3 AFR-LMS-003.4 AFR-LMS-007.2 AFR-LMS-007.3 BR-LMS-006
    # UC-LMS-015 / BW-LMS-01 / BW-LMS-03: all journey operations use HTTP.
    urls = [schedule(world, kind) for kind in ("assignments", "materials")]
    for url in urls:
        eventually(
            lambda url=url: world.actor("student").get(url).status_code,
            lambda status: status == 200,
        )
    assert (
        world.actor("student")
        .post(urls[0] + "submissions/", {"kind": "TEXT", "text": "My work"}, format="json")
        .status_code
        == 201
    )


@pytest.mark.parametrize("kind", ["assignments", "materials"])
def test_uc_lms_015_withdrawal_cancels_visible_release(world, release_worker, kind):
    url = schedule(world, kind)
    response = world.actor().post(url + "withdraw/", {}, format="json")
    assert response.status_code == 200 and response.json()["state"] == "DRAFT"
    time.sleep(2)
    assert world.actor("student").get(url).status_code == 404
    assert world.actor().get(url).json()["state"] == "DRAFT"


def test_uc_lms_015_processing_failure_remains_private(world, release_worker, monkeypatch, caplog):
    url = schedule(world, "materials")

    def failure(row, kind):
        raise RuleViolation("Ask the instructor to correct the content before retrying.")

    monkeypatch.setattr("modules.lms.services.releases._validate", failure)
    eventually(lambda: caplog.text, lambda text: "lms.release.validation_failed" in text)
    assert world.actor("student").get(url).status_code == 404
    response = world.actor().get(url)
    assert response.json()["state"] == "SCHEDULED" and response.json()["published_at"] is None
