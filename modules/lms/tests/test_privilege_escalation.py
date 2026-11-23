import inspect

import pytest
from django.conf import settings
from rest_framework.test import APIClient

from conftest import make_session
from core.api.csrf import token_for
from fusion_auth.client import IamUnavailable
from modules.lms.api import views
from modules.lms.api.urls import urlpatterns
from modules.lms.models import CoursePolicyVersion, GradeAuditLog
from modules.lms.registry import PERMISSIONS, ROLE_GRANTS
from modules.lms.tests.conftest import KEY, available, submit

pytestmark = pytest.mark.django_db
BASE = "/api/v1/lms"
ENDPOINTS = [(str(pattern.pattern), pattern.callback.view_class) for pattern in urlpatterns]


@pytest.mark.parametrize("path,view", ENDPOINTS)
def test_every_route_refuses_anonymous_missing_permission_missing_module(
    world, stub_iam, path, view
):
    path = BASE + "/" + path.replace("<int:pk>", str(world.workspace.pk))
    for method, permission in view.permission_map.items():
        stub_iam(None)
        assert getattr(APIClient(), method.lower())(path, {}, format="json").status_code == 401
        assert (
            getattr(world.actor(permissions=[]), method.lower())(
                path, {}, format="json"
            ).status_code
            == 403
        )
        assert (
            getattr(world.actor(permissions=[permission], modules=[]), method.lower())(
                path, {}, format="json"
            ).status_code
            == 403
        )


def test_permission_codes_match_real_registry_and_fake_surface():
    codes = {code for code, _ in PERMISSIONS}
    for _, view in ENDPOINTS:
        assert set(view.permission_map.values()) <= codes
    assert all(set(grants) <= codes for grants in ROLE_GRANTS.values())
    assert {cls for _, cls in ENDPOINTS} == {
        value
        for value in vars(views).values()
        if inspect.isclass(value) and value.__module__ == views.__name__
    }


def test_acting_role_not_union_of_designations_and_revoke_is_live(world):
    # BR-LMS-001/002: even a faculty holder acts only as the selected student.
    client = world.actor(
        "student", roles=("student", "faculty"), permissions=ROLE_GRANTS["faculty"]
    )
    assert (
        client.patch(
            f"{BASE}/courses/{world.workspace.pk}/", {"syllabus": "Escalate"}, format="json"
        ).status_code
        == 403
    )
    world.fake.course_associations = []
    assert client.get(f"{BASE}/courses/{world.workspace.pk}/").status_code == 404
    assert client.get(f"{BASE}/courses/").json()["results"] == []


def test_course_outage_returns_503_never_cached_membership(world):
    client = world.actor("student")
    world.fake.courses_error = IamUnavailable("synthetic service outage")
    response = client.get(f"{BASE}/courses/")
    assert response.status_code == 503
    assert "synthetic service outage" not in response.content.decode()


def test_unknown_active_role_is_403(world, stub_iam):
    client = world.actor()
    world.fake.session = make_session(
        user_id=1,
        modules=("lms",),
        permissions=ROLE_GRANTS["faculty"],
        roles=("faculty",),
        active_role="unknown",
    )
    assert client.get(f"{BASE}/courses/").status_code == 403


def test_cookie_write_requires_session_bound_csrf(world):
    world.actor()
    client = APIClient()
    client.cookies[settings.IAM_AUTH_COOKIE_NAME] = "cookie-session"
    url = f"{BASE}/courses/{world.workspace.pk}/"
    assert client.patch(url, {"schedule": "Changed"}, format="json").status_code == 403
    assert (
        client.patch(
            url,
            {"schedule": "Changed"},
            format="json",
            HTTP_X_CSRF_TOKEN=token_for("cookie-session"),
        ).status_code
        == 200
    )


def test_student_peer_and_observer_cannot_read_or_write_individual_data(world):
    # Source obligations: CFR-LMS-014 CFR-LMS-015 AFR-LMS-014.1 AFR-LMS-014.2 AFR-LMS-014.3
    #  AFR-LMS-014.4 AFR-LMS-014.5 AFR-LMS-015.1 AFR-LMS-015.2 AFR-LMS-015.3 AFR-LMS-015.4
    #  BR-LMS-003 BR-LMS-004
    # CFR-LMS-014/015, AFR-LMS-014.1 through .5; Observer no student-specific fields.
    row = available(world)
    submission = submit(world, row)
    world.actor().post(
        f"{BASE}/submissions/{submission['id']}/grade/", {"points": "12"}, format="json"
    )
    world.actor().post(f"{BASE}/submissions/{submission['id']}/grade/release/", {}, format="json")
    world.fake.course_associations.append(
        {
            "user_id": 5,
            "offering_key": KEY,
            "course_role": "STUDENT",
            "source_origin": "fusion_registration",
        }
    )
    peer = world.actor("student", uid=5)
    assert peer.get(f"{BASE}/submissions/{submission['id']}/").status_code == 404
    assert peer.get(f"{BASE}/submissions/{submission['id']}/download/").status_code == 404
    assert peer.get(f"{BASE}/courses/{world.workspace.pk}/grades/").json()["results"] == []
    assert (
        peer.get(f"{BASE}/assignments/{row['id']}/submissions/?user_id=2").json()["results"] == []
    )
    observer = world.actor("lms_observer")
    for path in (
        f"submissions/{submission['id']}/",
        f"submissions/{submission['id']}/download/",
        f"courses/{world.workspace.pk}/grades/",
        f"assignments/{row['id']}/submissions/",
    ):
        assert observer.get(f"{BASE}/{path}").status_code == 403
    for role in ("student", "lms_ta", "lms_observer"):
        client = world.actor(role)
        for path, data in (
            (f"assignments/{row['id']}/", {"instructions": "Escalate"}),
            (f"courses/{world.workspace.pk}/", {"schedule": "Changed"}),
        ):
            assert client.patch(f"{BASE}/{path}", data, format="json").status_code == 403
        assert (
            client.post(
                f"{BASE}/courses/{world.workspace.pk}/materials/",
                {"kind": "NOTE", "text": "Denied"},
                format="json",
            ).status_code
            == 403
        )
    observer = world.actor("lms_observer")
    data = observer.get(f"{BASE}/courses/{world.workspace.pk}/").json()
    assert not {"students", "submissions", "grades", "roster"} & data.keys()


def test_cross_course_section_id_is_checked_before_material_write(world):
    from modules.lms.models import Material, MaterialSection

    section = MaterialSection.objects.create(workspace=world.other, kind="MODULE", label="Other")
    response = world.actor().post(
        f"{BASE}/courses/{world.workspace.pk}/materials/",
        {"kind": "NOTE", "text": "Notes", "section_id": section.pk},
        format="json",
    )
    assert response.status_code == 404 and Material.objects.count() == 0


def test_observer_cannot_write_any_registered_endpoint(world):
    client = world.actor("lms_observer")
    for path, view in ENDPOINTS:
        for method in set(view.permission_map) - {"GET"}:
            url = BASE + "/" + path.replace("<int:pk>", str(world.workspace.pk))
            assert getattr(client, method.lower())(url, {}, format="json").status_code == 403


def test_ta_cannot_create_or_edit_course_structure(world):
    client = world.actor("lms_ta")
    assert (
        client.post(
            f"{BASE}/courses/{world.workspace.pk}/sections/",
            {"kind": "MODULE", "label": "Denied"},
            format="json",
        ).status_code
        == 403
    )
    assert (
        client.patch(f"{BASE}/sections/999999/", {"label": "Denied"}, format="json").status_code
        == 403
    )


def test_grade_and_audit_rollback_together(world, monkeypatch):
    from modules.lms.models import Grade

    row = submit(world, available(world))
    url = f"{BASE}/submissions/{row['id']}/grade/"
    assert world.actor().post(url, {"points": "10"}, format="json").status_code == 200
    assert world.actor().post(url + "release/", {}, format="json").status_code == 200

    def fail(**kwargs):
        raise RuntimeError("Simulated audit insert failure")

    monkeypatch.setattr(GradeAuditLog.objects, "create", fail)
    with pytest.raises(RuntimeError):
        world.actor().patch(url, {"points": "20", "feedback": "Must roll back"}, format="json")
    grade = Grade.objects.get()
    assert grade.points == 10 and grade.feedback == "" and GradeAuditLog.objects.count() == 2


def test_historical_rows_are_append_only(world):
    policy = CoursePolicyVersion.objects.get(workspace=world.workspace)
    with pytest.raises(ValueError):
        policy.save()
    with pytest.raises(ValueError):
        policy.delete()
    with pytest.raises(ValueError):
        CoursePolicyVersion.objects.filter(pk=policy.pk).update(can_ta_post_announcements=True)
    with pytest.raises(ValueError):
        CoursePolicyVersion.objects.filter(pk=policy.pk).delete()


def test_write_throttling_and_malformed_input(world, settings):
    from django.core.cache import cache

    settings.REST_FRAMEWORK = {
        **settings.REST_FRAMEWORK,
        "DEFAULT_THROTTLE_RATES": {
            **settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"],
            "lms_write": "1/hour",
        },
    }
    from core.api.throttling import PrincipalScopedThrottle

    # DRF resolves the settings once; pin the rate on its real throttle class for this request pair.
    original = PrincipalScopedThrottle.THROTTLE_RATES
    PrincipalScopedThrottle.THROTTLE_RATES = {**original, "lms_write": "1/hour"}
    try:
        client = world.actor()
        url = f"{BASE}/courses/{world.workspace.pk}/assignments/"
        assert client.post(url, {}, format="json").status_code == 400
        assert client.post(url, {}, format="json").status_code == 429
    finally:
        PrincipalScopedThrottle.THROTTLE_RATES = original
        cache.clear()
