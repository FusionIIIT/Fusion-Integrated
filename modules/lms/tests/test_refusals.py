from datetime import timedelta

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone
from freezegun import freeze_time

from modules.lms.models import Assignment, Material, Submission
from modules.lms.tests.conftest import available, draft, submit

pytestmark = pytest.mark.django_db


def test_database_uniqueness_survives_service_bypass(world):
    # D-05 is also enforced by the database, independently of the serialized service.
    row = submit(world, available(world))
    original = Submission.objects.get(pk=row["id"])
    with pytest.raises(IntegrityError), transaction.atomic():
        Submission.objects.create(
            assignment=original.assignment,
            user_id=original.user_id,
            kind="TEXT",
            text="Duplicate",
            submitted_at=timezone.now(),
        )
    assert Submission.objects.count() == 1


def test_each_resource_refuses_an_out_of_course_identifier(world):
    row = available(world)
    submission = submit(world, row)
    item = (
        world.actor()
        .post(
            f"/api/v1/lms/courses/{world.workspace.pk}/materials/",
            {"kind": "NOTE", "text": "Notes"},
            format="json",
        )
        .json()
    )
    world.fake.course_associations = [
        {"user_id": 1, "course_role": "FACULTY", "offering_key": world.other.external_offering_key},
    ]
    client = world.actor()
    for path in (
        f"materials/{item['id']}/",
        f"materials/{item['id']}/download/",
        f"assignments/{row['id']}/",
        f"assignments/{row['id']}/download/",
        f"assignments/{row['id']}/submissions/",
        f"submissions/{submission['id']}/",
        f"courses/{world.workspace.pk}/materials/",
        f"courses/{world.workspace.pk}/announcements/",
        f"courses/{world.workspace.pk}/assignments/",
        f"courses/{world.workspace.pk}/grades/",
    ):
        assert client.get("/api/v1/lms/" + path).status_code == 404
    for path in (
        f"assignments/{row['id']}/publish/",
        f"materials/{item['id']}/publish/",
        f"submissions/{submission['id']}/grade/",
        f"submissions/{submission['id']}/grade/release/",
    ):
        assert (
            client.post(
                "/api/v1/lms/" + path,
                {"points": "10"} if path.endswith("/grade/") else {},
                format="json",
            ).status_code
            == 404
        )


def test_semantically_invalid_writes_do_not_change_existing_state(world):
    row = draft(world)
    path = f"/api/v1/lms/assignments/{row['id']}/"
    for data in ({"instructions": " "}, {"points_possible": "-0.01"}):
        response = world.actor().patch(path, data, format="json")
        assert response.status_code == 422
    stored = Assignment.objects.get()
    assert stored.instructions == "Implement the exercise" and stored.state == "DRAFT"
    for kind, data in (
        ("material", {"kind": "LINK", "url": "javascript:alert(1)"}),
        ("announcement", {"content": " "}),
    ):
        response = world.actor().post(
            f"/api/v1/lms/courses/{world.workspace.pk}/{kind}s/", data, format="json"
        )
        assert response.status_code in (400, 422)
    # A second publish is a lifecycle conflict and cannot change attribution.
    response = world.actor().post(path + "publish/", {}, format="json")
    assert response.status_code == 200
    assert world.actor().post(path + "publish/", {}, format="json").status_code == 409


def test_scheduled_reschedule_rejects_stale_eta_and_allows_due_release(world, monkeypatch):
    from modules.lms.services.releases import release_one

    monkeypatch.setattr("modules.lms.tasks.release_content.apply_async", lambda **kwargs: None)
    row = draft(world)
    now = timezone.now()
    path = f"/api/v1/lms/assignments/{row['id']}/publish/"
    client = world.actor()
    assert (
        client.post(
            path, {"release_at": (now - timedelta(seconds=1)).isoformat()}, format="json"
        ).status_code
        == 422
    )
    assert (
        client.post(
            path, {"release_at": (now + timedelta(minutes=1)).isoformat()}, format="json"
        ).status_code
        == 200
    )
    assert (
        client.post(
            path, {"release_at": (now + timedelta(minutes=2)).isoformat()}, format="json"
        ).status_code
        == 200
    )
    with freeze_time(now + timedelta(minutes=1)):
        assert not release_one("assignment", row["id"])
    with freeze_time(now + timedelta(minutes=2)):
        assert release_one("assignment", row["id"])


def test_link_submission_and_missing_status(world):
    row = available(world, submission_type="LINK")
    url = f"/api/v1/lms/assignments/{row['id']}/submissions/"
    client = world.actor("student")
    assert client.get(url).json()["results"] == []
    response = client.post(url, {"kind": "LINK", "url": "https://example.org/work"}, format="json")
    assert response.status_code == 201 and response.json()["url"] == "https://example.org/work"


def test_course_metadata_outage_does_not_expose_partial_information(world, monkeypatch):
    from fusion_auth.client import IamUnavailable

    client = world.actor("student")

    def fail(*args, **kwargs):
        raise IamUnavailable("Synthetic metadata failure")

    monkeypatch.setattr(world.fake, "get_course_offerings", fail)
    assert client.get("/api/v1/lms/courses/").status_code == 503


def test_student_without_prior_optional_fields_and_no_policy_is_supported(world):
    from modules.lms.models import CourseWorkspace

    CourseWorkspace.objects.filter(pk=world.workspace.pk).update(details_published_at=None)
    response = world.actor("student").get(f"/api/v1/lms/courses/{world.workspace.pk}/")
    assert response.status_code == 200 and response.json()["syllabus"] == ""
    assert response.json()["schedule"] == "" and response.json()["staff"] == []
    # Safe default remains false even on an unseeded workspace associated by real IAM.
    world.fake.course_associations.append(
        {"user_id": 3, "course_role": "TA", "offering_key": world.other.external_offering_key}
    )
    response = world.actor("lms_ta").post(
        f"/api/v1/lms/courses/{world.other.pk}/announcements/", {"content": "Denied"}, format="json"
    )
    assert response.status_code == 403


def test_material_order_and_section_clear_edit(world):
    client = world.actor()
    url = f"/api/v1/lms/courses/{world.workspace.pk}/materials/"
    item = client.post(url, {"kind": "NOTE", "text": "Notes"}, format="json").json()
    response = client.patch(
        f"/api/v1/lms/materials/{item['id']}/", {"section_id": None, "order": 3}, format="json"
    )
    assert response.status_code == 200 and response.json()["section_id"] is None
    assert Material.objects.get().order == 3
