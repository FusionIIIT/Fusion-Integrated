"""Targeted tests to thoroughly cover services, selectors, views, and schedule (R1-01)."""

from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from core.api.exceptions import BadRequestError, NotFoundError, PermissionDeniedError
from modules.lms import schedule, selectors, services
from modules.lms.domain.constants import (
    AssignmentStatus,
    CourseRole,
    MaterialStatus,
    MaterialType,
    MembershipStatus,
    SubmissionType,
)
from modules.lms.models import (
    Assignment,
    AssignmentSubmission,
    CourseAnnouncement,
    CourseMaterial,
    CourseMembership,
    CourseWorkspace,
)

pytestmark = pytest.mark.django_db


def test_schedule_module_imports():
    assert "lms.process_scheduled_content_release" in schedule.TASK_ROUTES
    assert "lms.process-scheduled-content-release" in schedule.BEAT_SCHEDULE


def test_workspace_service_branches():
    p_inst = make_session(user_id=101, kind="faculty", modules=("lms",))
    p_stu = make_session(user_id=102, kind="student", modules=("lms",))

    # Student cannot update course details -> PermissionDeniedError
    with pytest.raises(PermissionDeniedError):
        services.update_course_details(99999, "Syllabus", "Schedule", p_stu)

    # Instructor updates course details (creates workspace if not present)
    CourseMembership.objects.create(
        course_id=99999,
        user_id=101,
        role=CourseRole.INSTRUCTOR,
        status=MembershipStatus.ACTIVE,
    )
    ws = services.update_course_details(99999, "Syllabus v1", "Schedule v1", p_inst)
    assert ws.syllabus == "Syllabus v1"
    assert ws.schedule_info == "Schedule v1"

    # Configure membership
    member = services.configure_membership(710, 101, CourseRole.INSTRUCTOR)
    assert member.course_id == 710
    assert member.user_id == 101


def test_materials_service_branches():
    p_inst = make_session(user_id=201, kind="faculty", modules=("lms",))
    p_stu = make_session(user_id=202, kind="student", modules=("lms",))

    course_id = 720
    CourseWorkspace.objects.create(course_id=course_id, course_code="CS720", title="Materials Course")
    CourseMembership.objects.create(course_id=course_id, user_id=201, role=CourseRole.INSTRUCTOR, status=MembershipStatus.ACTIVE)

    # File exceeding 20MB limit (20 * 1024 * 1024 + 10 bytes)
    big_file = SimpleUploadedFile("huge.pdf", b"x" * (20 * 1024 * 1024 + 10))
    with pytest.raises(BadRequestError, match="cannot exceed 20 MB"):
        services.create_material(
            course_id=course_id,
            title="Too Big",
            description="",
            material_type=MaterialType.FILE,
            content_text=None,
            external_url=None,
            file_attachment=big_file,
            section_name="General",
            sort_order=0,
            release_date=None,
            principal=p_inst,
        )

    # Student cannot create material -> PermissionDeniedError
    with pytest.raises(PermissionDeniedError):
        services.create_material(
            course_id=course_id,
            title="Student Upload",
            description="",
            material_type=MaterialType.NOTE,
            content_text="Forbidden note",
            external_url=None,
            file_attachment=None,
            section_name="General",
            sort_order=0,
            release_date=None,
            principal=p_stu,
        )

    # Delete material
    mat = CourseMaterial.objects.create(
        course_id=course_id,
        title="To Delete",
        material_type=MaterialType.NOTE,
        content_text="Delete me",
        status=MaterialStatus.PUBLISHED,
        uploaded_by=201,
    )
    with pytest.raises(PermissionDeniedError):
        services.delete_material(mat.id, p_stu)

    services.delete_material(mat.id, p_inst)
    assert not CourseMaterial.objects.filter(id=mat.id).exists()

    with pytest.raises(NotFoundError):
        services.delete_material(99997, p_inst)


def test_announcements_service_branches():
    p_inst = make_session(user_id=301, kind="faculty", modules=("lms",))
    p_stu = make_session(user_id=302, kind="student", modules=("lms",))

    course_id = 730
    CourseWorkspace.objects.create(course_id=course_id, course_code="CS730", title="Announcements Course")
    CourseMembership.objects.create(course_id=course_id, user_id=301, role=CourseRole.INSTRUCTOR, status=MembershipStatus.ACTIVE)

    # Empty title or content -> BadRequestError
    with pytest.raises(BadRequestError, match="title cannot be empty"):
        services.post_announcement(course_id, "", "Content", p_inst)
    with pytest.raises(BadRequestError, match="content cannot be empty"):
        services.post_announcement(course_id, "Title", "", p_inst)

    # Student cannot post announcement -> PermissionDeniedError
    with pytest.raises(PermissionDeniedError):
        services.post_announcement(course_id, "Title", "Body", p_stu)

    ann = CourseAnnouncement.objects.create(
        course_id=course_id,
        title="Ann 1",
        content="Content 1",
        author_id=301,
        author_role=CourseRole.INSTRUCTOR,
    )

    with pytest.raises(PermissionDeniedError):
        services.delete_announcement(ann.id, p_stu)

    services.delete_announcement(ann.id, p_inst)
    assert not CourseAnnouncement.objects.filter(id=ann.id).exists()

    with pytest.raises(NotFoundError):
        services.delete_announcement(99995, p_inst)


def test_assignments_service_branches():
    p_inst = make_session(user_id=401, kind="faculty", modules=("lms",))
    p_stu = make_session(user_id=402, kind="student", modules=("lms",))
    now = timezone.now()

    course_id = 740
    CourseWorkspace.objects.create(course_id=course_id, course_code="CS740", title="Assignments Course")
    CourseMembership.objects.create(course_id=course_id, user_id=401, role=CourseRole.INSTRUCTOR, status=MembershipStatus.ACTIVE)

    # Negative points -> BadRequestError
    with pytest.raises(BadRequestError):
        services.create_assignment(
            course_id=course_id,
            title="Bad Points",
            instructions="Inst",
            points_possible=-10,
            submission_type=SubmissionType.TEXT,
            due_date=now + timedelta(days=5),
            release_date=None,
            principal=p_inst,
        )

    # Non-instructor creates assignment
    with pytest.raises(PermissionDeniedError):
        services.create_assignment(
            course_id=course_id,
            title="Title",
            instructions="Inst",
            points_possible=100,
            submission_type=SubmissionType.TEXT,
            due_date=now + timedelta(days=5),
            release_date=None,
            principal=p_stu,
        )

    asg = services.create_assignment(
        course_id=course_id,
        title="Assignment Edit",
        instructions="Initial inst",
        points_possible=100,
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=5),
        release_date=None,
        principal=p_inst,
    )

    # Student tries to update
    with pytest.raises(PermissionDeniedError):
        services.update_assignment(
            asg.id,
            "Hacked",
            "Hacked inst",
            100,
            SubmissionType.TEXT,
            now + timedelta(days=5),
            None,
            p_stu,
        )

    # Instructor updates assignment
    updated = services.update_assignment(
        asg.id,
        "Updated Title",
        "New inst",
        90,
        SubmissionType.TEXT,
        now + timedelta(days=5),
        None,
        p_inst,
    )
    assert updated.title == "Updated Title"

    # Update non-existent
    with pytest.raises(NotFoundError):
        services.update_assignment(
            99993,
            "Ghost",
            "Ghost inst",
            90,
            SubmissionType.TEXT,
            now + timedelta(days=5),
            None,
            p_inst,
        )

    # Publish non-existent
    with pytest.raises(NotFoundError):
        services.publish_assignment(99992, release_date=None, principal=p_inst)

    # Student publishes
    with pytest.raises(PermissionDeniedError):
        services.publish_assignment(asg.id, release_date=None, principal=p_stu)

    # Delete assignment
    with pytest.raises(PermissionDeniedError):
        services.delete_assignment(asg.id, principal=p_stu)

    services.delete_assignment(asg.id, principal=p_inst)
    assert not Assignment.objects.filter(id=asg.id).exists()

    with pytest.raises(NotFoundError):
        services.delete_assignment(99991, principal=p_inst)


def test_submissions_service_branches():
    _p_inst = make_session(user_id=501, kind="faculty", modules=("lms",))
    p_stu = make_session(user_id=502, kind="student", modules=("lms",))
    p_outsider = make_session(user_id=503, kind="student", modules=("lms",))
    now = timezone.now()

    course_id = 750
    CourseWorkspace.objects.create(course_id=course_id, course_code="CS750", title="Submissions Course")
    CourseMembership.objects.create(course_id=course_id, user_id=501, role=CourseRole.INSTRUCTOR, status=MembershipStatus.ACTIVE)
    CourseMembership.objects.create(course_id=course_id, user_id=502, role=CourseRole.STUDENT, status=MembershipStatus.ACTIVE)

    asg = Assignment.objects.create(
        course_id=course_id,
        title="File Asg",
        instructions="Upload code",
        points_possible=100,
        submission_type=SubmissionType.FILE,
        due_date=now + timedelta(days=5),
        status=AssignmentStatus.PUBLISHED,
        created_by=501,
    )

    # Non-existent assignment
    with pytest.raises(NotFoundError):
        services.submit_assignment(99990, SubmissionType.FILE, None, None, None, p_stu)

    # Outsider student not enrolled in course
    with pytest.raises(PermissionDeniedError, match="registered course students"):
        services.submit_assignment(asg.id, SubmissionType.FILE, None, None, None, p_outsider)

    # Big file upload > 20MB
    big_file = SimpleUploadedFile("big.zip", b"z" * (20 * 1024 * 1024 + 10))
    with pytest.raises(BadRequestError, match="cannot exceed 20 MB"):
        services.submit_assignment(asg.id, SubmissionType.FILE, None, None, big_file, p_stu)


def test_grading_service_branches():
    p_inst = make_session(user_id=601, kind="faculty", modules=("lms",))

    # Grade non-existent submission
    with pytest.raises(NotFoundError):
        services.grade_submission(99989, 90, "Good", p_inst)

    # Update non-existent grade
    with pytest.raises(NotFoundError):
        services.update_grade(99988, 95, "New", "Reason", p_inst)

    # Publish grades for non-existent assignment
    with pytest.raises(NotFoundError):
        services.publish_grades(99987, [1], p_inst)


def test_api_crud_and_error_branches(stub_iam):
    stub_iam(
        make_session(
            user_id=701,
            kind="faculty",
            permissions=(
                "lms.workspace.view",
                "lms.workspace.update",
                "lms.material.view",
                "lms.material.create",
                "lms.material.publish",
                "lms.material.update",
                "lms.material.delete",
                "lms.announcement.view",
                "lms.announcement.create",
                "lms.announcement.update",
                "lms.announcement.delete",
                "lms.assignment.view",
                "lms.assignment.create",
                "lms.assignment.update",
                "lms.assignment.delete",
                "lms.assignment.publish",
                "lms.submission.view",
                "lms.submission.review",
                "lms.grade.view",
                "lms.grade.create",
                "lms.grade.update",
                "lms.grade.publish",
            ),
            modules=("lms",),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token tok-701")
    now = timezone.now()

    course_id = 760
    CourseWorkspace.objects.create(course_id=course_id, course_code="CS760", title="API Test Course")
    CourseMembership.objects.create(course_id=course_id, user_id=701, role=CourseRole.INSTRUCTOR, status=MembershipStatus.ACTIVE)

    # Material list missing query param
    assert client.get("/api/v1/lms/materials/").status_code == 400
    assert client.get("/api/v1/lms/announcements/").status_code == 400
    assert client.get("/api/v1/lms/assignments/").status_code == 400

    # Material detail, patch, delete
    mat = CourseMaterial.objects.create(
        course_id=course_id,
        title="API Mat",
        material_type=MaterialType.NOTE,
        content_text="Notes",
        status=MaterialStatus.PUBLISHED,
        uploaded_by=701,
    )
    assert client.get(f"/api/v1/lms/materials/{mat.id}/").status_code == 200
    assert client.patch(f"/api/v1/lms/materials/{mat.id}/", data={"title": "Updated Mat"}, format="json").status_code == 200
    assert client.delete(f"/api/v1/lms/materials/{mat.id}/").status_code == 204

    # Announcement detail, patch, delete
    ann = CourseAnnouncement.objects.create(
        course_id=course_id,
        title="API Ann",
        content="Content",
        author_id=701,
        author_role=CourseRole.INSTRUCTOR,
    )
    assert client.patch(f"/api/v1/lms/announcements/{ann.id}/", data={"title": "Updated Ann"}, format="json").status_code == 200
    assert client.delete(f"/api/v1/lms/announcements/{ann.id}/").status_code == 204

    # Assignment detail, patch, delete
    asg = Assignment.objects.create(
        course_id=course_id,
        title="API Asg",
        instructions="Instructions",
        points_possible=100,
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=5),
        status=AssignmentStatus.DRAFT,
        created_by=701,
    )
    assert client.get(f"/api/v1/lms/assignments/{asg.id}/").status_code == 200
    assert client.patch(f"/api/v1/lms/assignments/{asg.id}/", data={"title": "Updated Asg"}, format="json").status_code == 200
    assert client.delete(f"/api/v1/lms/assignments/{asg.id}/").status_code == 204

    # Missing downloads
    assert client.get("/api/v1/lms/materials/99999/download/").status_code == 404
    assert client.get("/api/v1/lms/submissions/99999/download/").status_code == 404

    # Missing points on grade
    assert client.post("/api/v1/lms/submissions/1/grade/", data={}, format="json").status_code == 400
    assert client.patch("/api/v1/lms/submissions/1/grade/", data={}, format="json").status_code == 400


def test_selectors_submissions_and_grades(stub_iam):
    p_inst = make_session(user_id=801, kind="faculty", modules=("lms",))
    p_stu = make_session(user_id=802, kind="student", modules=("lms",))
    now = timezone.now()

    course_id = 770
    CourseWorkspace.objects.create(course_id=course_id, course_code="CS770", title="Selectors Course")
    CourseMembership.objects.create(course_id=course_id, user_id=801, role=CourseRole.INSTRUCTOR, status=MembershipStatus.ACTIVE)
    CourseMembership.objects.create(course_id=course_id, user_id=802, role=CourseRole.STUDENT, status=MembershipStatus.ACTIVE)

    asg = Assignment.objects.create(
        course_id=course_id,
        title="Selectors Asg",
        instructions="Inst",
        points_possible=100,
        submission_type=SubmissionType.TEXT,
        due_date=now + timedelta(days=5),
        status=AssignmentStatus.PUBLISHED,
        created_by=801,
    )
    sub = AssignmentSubmission.objects.create(
        assignment=asg,
        student_id=802,
        submission_type=SubmissionType.TEXT,
        content_text="Solution",
    )

    # get_submission_by_id
    assert selectors.get_submission_by_id(sub.id, p_inst) is not None
    assert selectors.get_submission_by_id(sub.id, p_stu) is not None
    assert selectors.get_submission_by_id(99999, p_inst) is None

    # list_course_grades
    grades = selectors.list_course_grades(asg.id, p_inst)
    assert isinstance(grades, list)


def test_lms_upload_root_check(tmp_path, settings):
    from modules.lms.checks import check_lms_upload_root

    settings.MEDIA_ROOT = None
    assert check_lms_upload_root(None) == []

    settings.MEDIA_ROOT = str(settings.BASE_DIR / "inside_repo")
    errors = check_lms_upload_root(None)
    assert any(e.id == "lms.files.E001" for e in errors)

    valid_dir = tmp_path / "valid_media"
    valid_dir.mkdir(parents=True, exist_ok=True)
    valid_dir.chmod(0o700)
    settings.MEDIA_ROOT = str(valid_dir)
    assert check_lms_upload_root(None) == []

    valid_dir.chmod(0o755)
    warnings = check_lms_upload_root(None)
    assert any(w.id == "lms.files.W001" for w in warnings)
