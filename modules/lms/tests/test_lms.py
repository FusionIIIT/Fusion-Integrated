from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_principal, make_session
from core.api.exceptions import ConflictError, DomainError, PermissionDeniedError
from modules.academics import contracts as academic
from modules.lms.models import Assignment, GradeAudit, Material, Submission, Workspace
from modules.lms.registry import PERMISSIONS
from modules.lms.services import courses as services

pytestmark = pytest.mark.django_db


@pytest.fixture
def lms(settings, monkeypatch, tmp_path):
    settings.LMS_COURSE_PROVIDER = "test.provider"
    settings.LMS_UPLOAD_ROOT = str(tmp_path)
    memberships = {
        uid: [
            {
                "course_id": 10,
                "year": 2026,
                "semester_type": "Odd Semester",
                "role": role,
                "code": "CS101",
                "title": "Course",
                "may_announce": False,
            }
        ]
        for uid, role in [
            (1, "student"),
            (2, "faculty"),
            (3, "ta"),
            (4, "observer"),
            (6, "student"),
        ]
    }
    memberships[5] = []
    monkeypatch.setattr(
        academic, "import_string", lambda path: lambda ids: {i: memberships.get(i, []) for i in ids}
    )
    space = Workspace.objects.create(course_id=10, year=2026, semester_type="Odd Semester")

    def actor(uid=1, active=None):
        names = {
            1: "student",
            2: "faculty",
            3: "Teaching Assistant",
            4: "Observer",
            5: "student",
            6: "student",
        }
        return make_principal(
            user_id=uid,
            kind="faculty" if uid == 2 else "student",
            active_role=active or names[uid],
            roles=(names[uid],),
            modules=("lms",),
            permissions=tuple(code for code, label in PERMISSIONS),
        )

    assignment = Assignment.objects.create(
        workspace=space,
        title="Task",
        instructions="Answer",
        submission_type="text",
        points_possible=10,
        due_at=timezone.now() + timedelta(days=1),
        state="published",
    )
    return {"space": space, "actor": actor, "assignment": assignment, "memberships": memberships}


def api(stub_iam, actor):
    stub_iam(
        make_session(
            user_id=actor.user_id,
            kind=actor.kind,
            roles=actor.roles,
            active_role=actor.active_role,
            modules=actor.modules,
            permissions=actor.permissions,
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token lms-test")
    return client


def test_provider_required_and_unknown_source_fails_closed(lms, settings):
    settings.LMS_COURSE_PROVIDER = ""
    with pytest.raises(academic.RegistrationUnavailable):
        services.open_courses(lms["actor"]())


def test_context_whitelists_observer_metadata(lms):
    lms["memberships"][4][0]["student_grades"] = [{"student": 1, "grade": 8}]
    rows = services.open_courses(lms["actor"](4))
    assert len(rows) == 1
    assert "student_grades" not in rows[0]


def test_wrong_active_role_cannot_use_an_association(lms):
    assert services.open_courses(lms["actor"](2, "Observer")) == []


@pytest.mark.parametrize("uid", [1, 3, 4])
def test_nonfaculty_cannot_write_materials(lms, uid):
    with pytest.raises(PermissionDeniedError):
        services.save_content(
            lms["actor"](uid),
            lms["space"].pk,
            "material",
            {"title": "Invalid", "kind": "text", "text": "Note"},
        )


def test_student_submission_is_owned_and_resubmission_unresolved(lms):
    row = services.submit(lms["actor"](), lms["space"].pk, lms["assignment"].pk, {"text": "Answer"})
    assert row.student_id == 1
    with pytest.raises(ConflictError) as error:
        services.submit(
            lms["actor"](), lms["space"].pk, lms["assignment"].pk, {"text": "Replacement"}
        )
    assert error.value.code == "resubmission_policy_unresolved"


def test_late_submission_and_wrong_type_are_not_saved(lms):
    lms["assignment"].due_at = timezone.now() - timedelta(seconds=1)
    lms["assignment"].save()
    with pytest.raises(DomainError) as error:
        services.submit(lms["actor"](), lms["space"].pk, lms["assignment"].pk, {"text": "Late"})
    assert error.value.code == "late_policy_unresolved"
    lms["assignment"].due_at = timezone.now() + timedelta(days=1)
    lms["assignment"].save()
    with pytest.raises(DomainError):
        services.submit(
            lms["actor"](), lms["space"].pk, lms["assignment"].pk, {"link": "https://example.org"}
        )
    assert not Submission.objects.exists()


def test_ta_grades_faculty_releases_with_audit_and_replay_guard(lms):
    row = services.submit(lms["actor"](), lms["space"].pk, lms["assignment"].pk, {"text": "Answer"})
    services.grade(
        lms["actor"](3),
        lms["space"].pk,
        row.pk,
        {"points": Decimal("8"), "feedback": "Good", "revision": 1},
    )
    row.refresh_from_db()
    assert row.grader_id == 3 and not row.released
    with pytest.raises(PermissionDeniedError):
        services.grade(lms["actor"](3), lms["space"].pk, row.pk, {"revision": 2}, release=True)
    services.grade(lms["actor"](2), lms["space"].pk, row.pk, {"revision": 2}, release=True)
    assert GradeAudit.objects.count() == 2
    with pytest.raises(ConflictError):
        services.grade(lms["actor"](2), lms["space"].pk, row.pk, {"revision": 2}, release=True)


def test_scheduled_content_releases_once(lms):
    Material.objects.create(
        workspace=lms["space"],
        title="Future",
        kind="text",
        text="N",
        state="scheduled",
        release_at=timezone.now() + timedelta(days=1),
    )
    due = Material.objects.create(
        workspace=lms["space"],
        title="Due",
        kind="text",
        text="N",
        state="scheduled",
        release_at=timezone.now() - timedelta(seconds=1),
    )
    assert services.release_due() == 1
    assert services.release_due() == 0
    due.refresh_from_db()
    assert due.state == "published"


def test_api_own_data_and_hidden_draft_feedback(lms, stub_iam):
    row = Submission.objects.create(
        assignment=lms["assignment"],
        student_id=1,
        text="Answer",
        points=8,
        feedback="Private draft",
    )
    Submission.objects.create(assignment=lms["assignment"], student_id=6, text="Other student")
    client = api(stub_iam, lms["actor"]())
    response = client.get(f"/api/v1/lms/courses/{lms['space'].pk}/")
    assert response.status_code == 200
    assert [s["student_id"] for s in response.json()["submissions"]] == [1]
    assert response.json()["submissions"][0]["points"] is None
    assert response.json()["submissions"][0]["feedback"] == ""
    row.released = True
    row.save()
    assert (
        client.get(f"/api/v1/lms/courses/{lms['space'].pk}/").json()["submissions"][0]["points"]
        == "8.00"
    )


def test_observer_has_no_student_records_or_draft_content(lms, stub_iam):
    Material.objects.create(
        workspace=lms["space"], title="Secret", kind="text", text="Hidden", state="draft"
    )
    Submission.objects.create(assignment=lms["assignment"], student_id=1, text="Student work")
    client = api(stub_iam, lms["actor"](4))
    response = client.get(f"/api/v1/lms/courses/{lms['space'].pk}/")
    assert response.status_code == 200
    data = response.json()
    assert data["submissions"] == [] and data["assignments"] == [] and data["materials"] == []
    assert (
        client.post(
            f"/api/v1/lms/courses/{lms['space'].pk}/write/material/",
            {"title": "Bad"},
            format="json",
        ).status_code
        == 403
    )


def test_foreign_course_is_not_found(lms, stub_iam):
    response = api(stub_iam, lms["actor"](5)).get(f"/api/v1/lms/courses/{lms['space'].pk}/")
    assert response.status_code == 404


def test_private_upload_and_cross_student_download(lms, stub_iam):
    lms["assignment"].submission_type = "file"
    lms["assignment"].save()
    client = api(stub_iam, lms["actor"]())
    response = client.post(
        f"/api/v1/lms/courses/{lms['space'].pk}/assignments/{lms['assignment'].pk}/submit/",
        {"file": SimpleUploadedFile("answer.txt", b"Own answer")},
        format="multipart",
    )
    assert response.status_code == 201, response.content
    path = response.json()["download_url"]
    assert client.get(path).status_code == 200
    assert api(stub_iam, lms["actor"](6)).get(path).status_code == 404
    assert api(stub_iam, lms["actor"](4)).get(path).status_code == 404


def test_api_faculty_authoring_and_publish(lms, stub_iam):
    client = api(stub_iam, lms["actor"](2))
    response = client.post(
        f"/api/v1/lms/courses/{lms['space'].pk}/write/assignment/",
        {
            "title": "New",
            "instructions": "Work",
            "submission_type": "text",
            "points_possible": "10",
            "due_at": (timezone.now() + timedelta(days=2)).isoformat(),
        },
        format="json",
    )
    assert response.status_code == 201, response.content
    assignment_id = response.json()["id"]
    assert Assignment.objects.get(pk=assignment_id).state == "draft"
    assert (
        client.post(
            f"/api/v1/lms/courses/{lms['space'].pk}/assignments/{assignment_id}/publish/"
        ).status_code
        == 200
    )
