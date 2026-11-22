from datetime import timedelta

import pytest
from django.utils import timezone
from freezegun import freeze_time

from config.celery import app
from modules.lms.models import Material
from modules.lms.schedule import BEAT_SCHEDULE
from modules.lms.services.releases import release_one
from modules.lms.tasks import release_content, release_due_materials
from modules.lms.tests.conftest import draft

pytestmark = pytest.mark.django_db


def test_schedule_is_merged_and_catchup_is_bounded(world):
    for key, entry in BEAT_SCHEDULE.items():
        assert app.conf.beat_schedule[key] == entry and entry["schedule"] == 60.0
    for _ in range(51):
        Material.objects.create(
            workspace=world.workspace,
            kind="NOTE",
            text="Notes",
            author_user_id=1,
            state="SCHEDULED",
            release_at=timezone.now() - timedelta(minutes=1),
        )
    assert release_due_materials() == 50
    assert Material.objects.filter(state="SCHEDULED").count() == 1
    assert release_due_materials() == 1
    assert release_due_materials() == 0


def test_eta_registered_only_after_commit_and_withdrawn_content_stays_private(
    world, monkeypatch, django_capture_on_commit_callbacks
):
    calls = []
    monkeypatch.setattr(
        "modules.lms.tasks.release_content.apply_async", lambda **kwargs: calls.append(kwargs)
    )
    row = draft(world)
    now = timezone.now()
    url = f"/api/v1/lms/assignments/{row['id']}"
    with django_capture_on_commit_callbacks(execute=True):
        response = world.actor().post(
            url + "/publish/",
            {"release_at": (now + timedelta(minutes=1)).isoformat()},
            format="json",
        )
        assert response.status_code == 200 and calls == []
    assert len(calls) == 1 and calls[0]["args"] == ("assignment", row["id"])
    assert world.actor().post(url + "/withdraw/", {}, format="json").json()["state"] == "DRAFT"
    with freeze_time(now + timedelta(minutes=2)):
        assert not release_one("assignment", row["id"])
        assert world.actor("student").get(url + "/").status_code == 404


def test_bad_content_failure_remains_unpublished_and_logged(world, caplog):
    row = Material.objects.create(
        workspace=world.workspace,
        kind="NOTE",
        text=" ",
        author_user_id=1,
        state="SCHEDULED",
        release_at=timezone.now() - timedelta(seconds=1),
    )
    assert release_content("material", row.pk) is False
    row.refresh_from_db()
    assert row.state == "SCHEDULED" and row.published_at is None
    assert "lms.release.validation_failed" in caplog.text


def test_missing_future_and_invalid_kind_tasks(world):
    assert not release_one("material", 999999)
    row = Material.objects.create(
        workspace=world.workspace,
        kind="NOTE",
        text="Notes",
        author_user_id=1,
        state="SCHEDULED",
        release_at=timezone.now() + timedelta(seconds=10),
    )
    assert not release_one("material", row.pk)
    with pytest.raises(ValueError):
        release_one("unknown", row.pk)
