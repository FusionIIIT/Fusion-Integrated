import io

import pytest
from django.apps import apps
from django.core.cache import cache
from django.core.management import call_command

from core.api.throttling import PrincipalScopedThrottle
from modules.lms.api.urls import urlpatterns
from modules.lms.models import ContentTransitionLog, GradeAuditLog
from modules.lms.registry import PERMISSIONS
from modules.lms.tests.conftest import available, draft, submit

pytestmark = pytest.mark.django_db
WRITES = [
    (str(pattern.pattern), method)
    for pattern in urlpatterns
    for method in pattern.callback.view_class.permission_map
    if method != "GET"
]


def snapshot():
    return {
        model._meta.label: list(model.objects.order_by("pk").values())
        for model in apps.get_app_config("lms").get_models()
    }


@pytest.mark.parametrize("path,method", WRITES)
def test_every_write_rejects_unknown_fields_without_side_effects(world, path, method):
    client = world.actor(permissions=[code for code, _ in PERMISSIONS])
    url = "/api/v1/lms/" + path.replace("<int:pk>", str(world.workspace.pk))
    before = snapshot()
    response = getattr(client, method.lower())(url, {"unrecognized": "x"}, format="json")
    assert response.status_code == 400, response.content
    assert snapshot() == before


@pytest.mark.parametrize("path,method", WRITES)
def test_every_write_throttle_refuses_without_side_effects(world, path, method, monkeypatch):
    cache.clear()
    monkeypatch.setattr(
        PrincipalScopedThrottle,
        "THROTTLE_RATES",
        {**PrincipalScopedThrottle.THROTTLE_RATES, "lms_write": "1/hour"},
    )
    client = world.actor(permissions=[code for code, _ in PERMISSIONS])
    url = "/api/v1/lms/" + path.replace("<int:pk>", str(world.workspace.pk))
    before = snapshot()
    try:
        assert (
            getattr(client, method.lower())(url, {"unknown": 1}, format="json").status_code == 400
        )
        response = getattr(client, method.lower())(url, {}, format="json")
        assert response.status_code == 429, response.content
        assert snapshot() == before
    finally:
        cache.clear()


def test_absent_and_repeated_grade_release_are_conflicts_without_audit_changes(world):
    row = submit(world, available(world))
    url = f"/api/v1/lms/submissions/{row['id']}/grade/"
    client = world.actor()
    assert client.post(url + "release/", {}, format="json").status_code == 409
    assert GradeAuditLog.objects.count() == 0
    assert client.post(url, {"points": "10"}, format="json").status_code == 200
    assert client.post(url + "release/", {}, format="json").status_code == 200
    before = snapshot()
    assert client.post(url + "release/", {}, format="json").status_code == 409
    assert snapshot() == before


def test_publication_audit_is_atomic_and_append_only(world, monkeypatch):
    row = draft(world)
    url = f"/api/v1/lms/assignments/{row['id']}/publish/"
    before = snapshot()

    def fail(**kwargs):
        raise RuntimeError("Synthetic transition audit failure")

    with monkeypatch.context() as patch:
        patch.setattr(ContentTransitionLog.objects, "create", fail)
        with pytest.raises(RuntimeError, match="audit failure"):
            world.actor().post(url, {}, format="json")
    assert snapshot() == before
    assert world.actor().post(url, {}, format="json").status_code == 200
    audit = ContentTransitionLog.objects.get()
    assert (audit.event, audit.old_state, audit.new_state, audit.actor_role) == (
        "publish",
        "DRAFT",
        "AVAILABLE",
        "FACULTY",
    )
    assert audit.actor_user_id == 1 and audit.assignment_id == row["id"]
    with pytest.raises(ValueError):
        ContentTransitionLog.objects.filter(pk=audit.pk).delete()


@pytest.mark.parametrize("kind", ["materials", "assignments"])
def test_operator_sweep_commands_are_available_and_idempotent(world, kind):
    output = io.StringIO()
    for _ in range(2):
        call_command(f"release_due_{kind}", stdout=output)
    assert output.getvalue().splitlines() == [f"Released 0 {kind}."] * 2
