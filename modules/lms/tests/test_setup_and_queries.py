import io
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.utils import OperationalError
from django.utils import timezone

from fusion_auth.client import IamUnavailable
from modules.lms import registry
from modules.lms.models import (
    Announcement,
    Assignment,
    CoursePolicyVersion,
    CourseWorkspace,
    Material,
)
from modules.lms.services import setup
from modules.lms.tests.conftest import KEY, OTHER_KEY

pytestmark = pytest.mark.django_db


def test_workspace_setup_is_idempotent_and_preserves_faculty_owned_details(world):
    world.workspace.syllabus = "Faculty-maintained content"
    world.workspace.save()
    world.fake.course_offerings.append(
        {"offering_key": "cof_" + "c" * 64, "syllabus": "Source syllabus"}
    )
    output = io.StringIO()
    call_command("sync_lms_workspaces", stdout=output)
    assert "Initialized 1" in output.getvalue()
    assert setup.sync_workspaces() == 0
    world.workspace.refresh_from_db()
    assert world.workspace.syllabus == "Faculty-maintained content"
    assert CourseWorkspace.objects.count() == 3 and CoursePolicyVersion.objects.count() == 3
    assert not CoursePolicyVersion.objects.filter(can_ta_post_announcements=True).exists()
    assert registry.readiness() == []
    call_command("check_lms_ready", stdout=output)
    assert "prerequisites satisfied" in output.getvalue()


def test_readiness_explains_migration_catalogue_policy_and_iam_failures(world, monkeypatch):
    assert "sync_lms_workspaces" in registry.readiness()[0]
    with pytest.raises(CommandError, match="sync_lms_workspaces"):
        call_command("check_lms_ready")
    world.fake.courses_error = IamUnavailable("Outage")
    assert "pinned IAM" in setup.unmet_prerequisites()[0]
    with pytest.raises(CommandError, match="IAM course catalogue unavailable"):
        call_command("sync_lms_workspaces")
    world.fake.courses_error = None

    def fail(*args, **kwargs):
        raise OperationalError("Missing table")

    monkeypatch.setattr(CourseWorkspace.objects, "values_list", fail)
    assert "migrate" in setup.unmet_prerequisites()[0]


@pytest.mark.parametrize(
    "resource,model,attrs",
    [
        ("materials", Material, {"kind": "NOTE", "text": "Notes", "state": "PUBLISHED"}),
        (
            "assignments",
            Assignment,
            {
                "instructions": "Work",
                "submission_type": "TEXT",
                "points_possible": 10,
                "state": "AVAILABLE",
            },
        ),
        ("announcements", Announcement, {"content": "News"}),
    ],
)
def test_list_query_counts_do_not_grow_from_two_to_twenty(
    world, django_assert_num_queries, resource, model, attrs
):
    attrs = {**attrs, "workspace": world.workspace, "author_user_id": 1}
    if resource != "announcements":
        attrs["published_at"] = timezone.now()
    if resource == "assignments":
        attrs["due_at"] = world.due
    client = world.actor("student")
    for _ in range(2):
        model.objects.create(**attrs)
    path = f"/api/v1/lms/courses/{world.workspace.pk}/{resource}/"
    with django_assert_num_queries(2):
        response = client.get(path)
        assert len(response.json()["results"]) == 2
    for _ in range(18):
        model.objects.create(**attrs)
    with django_assert_num_queries(2):
        response = client.get(path)
        assert len(response.json()["results"]) == 20


def test_course_query_budget_and_staff_contacts(world, django_assert_num_queries, user_ref):
    from modules.lms.tests.conftest import ACTORS

    def add(start, end):
        for index in range(start, end):
            key = "cof_" + f"{index:064x}"
            CourseWorkspace.objects.create(external_offering_key=key)
            world.fake.course_offerings.append({"offering_key": key, "course_code": f"SYN{index}"})
            world.fake.course_associations.append(
                {"user_id": 2, "course_role": "STUDENT", "offering_key": key}
            )

    # Include staff enrichment without one IAM request per course.
    client = world.actor("student")
    world.fake.users = {
        1: user_ref(1, name="Synthetic Faculty", kind="faculty"),
        3: user_ref(3, name="Synthetic TA"),
    }
    world.fake.course_associations.append(
        {"user_id": 2, "course_role": "STUDENT", "offering_key": OTHER_KEY}
    )
    with django_assert_num_queries(2):
        response = client.get("/api/v1/lms/courses/")
        assert len(response.json()["results"]) == 2
    add(10, 28)
    with django_assert_num_queries(2):
        response = client.get("/api/v1/lms/courses/")
        assert len(response.json()["results"]) == 20
    row = next(row for row in response.json()["results"] if row["external_offering_key"] == KEY)
    assert row["staff"][0]["display_name"] == "Synthetic Faculty"
    assert ACTORS["student"][0] == 2


def test_sections_edit_material_withdraw_and_nonfile_download(world):
    client = world.actor()
    created = client.post(
        f"/api/v1/lms/courses/{world.workspace.pk}/sections/",
        {"kind": "MODULE", "label": "Unit"},
        format="json",
    )
    pk = created.json()["id"]
    assert (
        client.patch(
            f"/api/v1/lms/sections/{pk}/", {"label": "Revised unit", "order": 2}, format="json"
        ).json()["label"]
        == "Revised unit"
    )
    item = client.post(
        f"/api/v1/lms/courses/{world.workspace.pk}/materials/",
        {"kind": "NOTE", "text": "Notes"},
        format="json",
    ).json()
    pk = item["id"]
    assert client.get(f"/api/v1/lms/materials/{pk}/download/").status_code == 404
    response = client.post(
        f"/api/v1/lms/materials/{pk}/publish/",
        {"release_at": (timezone.now() + timedelta(hours=1)).isoformat()},
        format="json",
    )
    assert response.json()["state"] == "SCHEDULED"
    assert (
        client.post(f"/api/v1/lms/materials/{pk}/withdraw/", {}, format="json").json()["state"]
        == "DRAFT"
    )


def test_eta_failure_is_logged_and_beat_can_recover(world, monkeypatch, caplog):
    from kombu.exceptions import OperationalError

    from modules.lms.services.releases import _queue

    def fail(**kwargs):
        raise OperationalError("Synthetic broker outage")

    monkeypatch.setattr("modules.lms.tasks.release_content.apply_async", fail)
    _queue("material", 1, timezone.now())
    assert "lms.release.dispatch_failed" in caplog.text


@pytest.mark.parametrize("resource", ["submissions", "grades"])
def test_submission_and_grade_lists_keep_constant_query_budget(
    world, django_assert_num_queries, resource
):
    from modules.lms.models import Grade, Submission

    assignment = Assignment.objects.create(
        workspace=world.workspace,
        instructions="Work",
        due_at=world.due,
        submission_type="TEXT",
        points_possible=20,
        state="AVAILABLE",
        published_at=timezone.now(),
        author_user_id=1,
    )
    client = world.actor()
    path = (
        f"/api/v1/lms/assignments/{assignment.pk}/submissions/"
        if resource == "submissions"
        else f"/api/v1/lms/courses/{world.workspace.pk}/grades/"
    )
    for count in (2, 20):
        for uid in range(Submission.objects.count() + 1, count + 1):
            submission = Submission.objects.create(
                assignment=assignment,
                user_id=uid,
                kind="TEXT",
                text="Work",
                submitted_at=timezone.now(),
            )
            Grade.objects.create(
                submission=submission, points=10, grader_user_id=1, graded_at=timezone.now()
            )
        with django_assert_num_queries(2):
            assert len(client.get(path).json()["results"]) == count
