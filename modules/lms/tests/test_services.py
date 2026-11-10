"""Integration tests for LMS Course Workspace and Materials services."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from fusion_auth.principal import Principal
from modules.lms.contracts import (
    get_assignment_deadlines,
    get_assignment_submissions,
    get_course_announcements,
    get_course_assignments,
)
from modules.lms.domain.entities import (
    AssignmentStatus,
    CourseRole,
    CourseStatus,
    DeadlineWindowStatus,
    MaterialStatus,
    MaterialType,
    SectionType,
    SubmissionStatus,
    SubmissionType,
)
from modules.lms.models import (
    Course,
    CourseAnnouncement,
    CourseAssignment,
    CourseAssignmentExtension,
    CourseMaterial,
    CourseMembership,
    CourseSubmission,
)
from modules.lms.selectors.announcements import (
    get_course_announcement_detail,
    list_course_announcements,
)
from modules.lms.selectors.assignments import (
    get_course_assignment_detail,
    list_course_assignments,
)
from modules.lms.selectors.deadlines import (
    calculate_deadline_info,
    get_assignment_deadline_info,
    list_assignment_extensions,
)
from modules.lms.selectors.submissions import (
    get_student_submission_history,
    get_submission_for_download,
    list_assignment_submissions,
)
from modules.lms.services import announcements as announcement_service
from modules.lms.services import assignments as assignment_service
from modules.lms.services import courses as course_service
from modules.lms.services import deadlines as deadline_service
from modules.lms.services import materials as material_service
from modules.lms.services import submissions as submission_service


def make_principal(user_id: int, role: str, permissions: tuple[str, ...]) -> Principal:
    from conftest import make_principal as _mp
    return _mp(
        user_id=user_id,
        kind=role,
        roles=(role,),
        active_role=role,
        permissions=permissions,
        modules=("lms",),
    )


@pytest.mark.django_db
def test_faculty_can_update_assigned_course_details():
    course = Course.objects.create(
        code="CS301",
        title="Database Systems",
        description="Core DBMS",
        syllabus="Initial syllabus",
        schedule="Mon 10:00",
        status=CourseStatus.PUBLISHED,
    )
    CourseMembership.objects.create(course=course, user_id=9001, role=CourseRole.FACULTY)

    faculty = make_principal(9001, "faculty", ("lms.course.view", "lms.course.manage"))

    updated = course_service.update_course_workspace(
        actor=faculty,
        course_code="CS301",
        syllabus="Updated detailed syllabus: Relational algebra, SQL, Normalization.",
        schedule="Mon/Wed 10:00-11:30",
    )

    assert updated.syllabus == "Updated detailed syllabus: Relational algebra, SQL, Normalization."
    assert updated.schedule == "Mon/Wed 10:00-11:30"
    assert updated.title == "Database Systems"


@pytest.mark.django_db
def test_unassigned_faculty_cannot_update_course():
    Course.objects.create(code="CS301", title="Database Systems")
    # Faculty 9002 has manage permission, but is NOT assigned to CS301
    faculty_unassigned = make_principal(9002, "faculty", ("lms.course.view", "lms.course.manage"))

    with pytest.raises(NotFoundError):
        course_service.update_course_workspace(
            actor=faculty_unassigned,
            course_code="CS301",
            syllabus="Sneaky syllabus",
        )


@pytest.mark.django_db
def test_ta_cannot_update_course_details():
    course = Course.objects.create(code="CS301", title="Database Systems")
    CourseMembership.objects.create(course=course, user_id=2001, role=CourseRole.TA)

    ta = make_principal(2001, "staff", ("lms.course.view", "lms.course.manage"))

    with pytest.raises(PermissionDeniedError, match="Only faculty assigned"):
        course_service.update_course_workspace(
            actor=ta,
            course_code="CS301",
            syllabus="TA syllabus edit attempt",
        )


@pytest.mark.django_db
def test_observer_cannot_update_course_details():
    course = Course.objects.create(code="CS301", title="Database Systems")
    CourseMembership.objects.create(course=course, user_id=3001, role=CourseRole.OBSERVER)

    observer = make_principal(3001, "staff", ("lms.course.view", "lms.course.manage"))

    with pytest.raises(PermissionDeniedError, match="Only faculty assigned"):
        course_service.update_course_workspace(
            actor=observer,
            course_code="CS301",
            syllabus="Observer edit attempt",
        )


@pytest.mark.django_db
def test_student_cannot_update_course_details():
    course = Course.objects.create(code="CS301", title="Database Systems")
    CourseMembership.objects.create(course=course, user_id=1001, role=CourseRole.STUDENT)

    student = make_principal(1001, "student", ("lms.course.view", "lms.course.manage"))

    with pytest.raises(PermissionDeniedError, match="Only faculty assigned"):
        course_service.update_course_workspace(
            actor=student,
            course_code="CS301",
            syllabus="Student edit attempt",
        )


@pytest.mark.django_db
def test_empty_title_update_rejected():
    course = Course.objects.create(code="CS301", title="Database Systems")
    CourseMembership.objects.create(course=course, user_id=9001, role=CourseRole.FACULTY)

    faculty = make_principal(9001, "faculty", ("lms.course.view", "lms.course.manage"))

    with pytest.raises(ConflictError, match="title cannot be empty"):
        course_service.update_course_workspace(
            actor=faculty,
            course_code="CS301",
            title="   ",
        )


@pytest.mark.django_db
def test_faculty_can_create_link_and_note_material():
    course = Course.objects.create(code="CS301", title="Database Systems")
    CourseMembership.objects.create(course=course, user_id=9001, role=CourseRole.FACULTY)

    faculty = make_principal(
        9001, "faculty", ("lms.course.view", "lms.material.manage")
    )

    mat_note = material_service.create_course_material(
        actor=faculty,
        course_code="CS301",
        title="Lecture 1 Overview",
        section_title="Module 1: Relational Model",
        material_type=MaterialType.NOTE,
        section_type=SectionType.MODULE,
        status=MaterialStatus.PUBLISHED,
        content="Key takeaways: Schema vs Instance, DDL, DML.",
    )
    assert mat_note.id is not None
    assert mat_note.material_type == MaterialType.NOTE
    assert mat_note.status == MaterialStatus.PUBLISHED

    mat_link = material_service.create_course_material(
        actor=faculty,
        course_code="CS301",
        title="PostgreSQL Manual",
        section_title="Module 1: Relational Model",
        material_type=MaterialType.LINK,
        link_url="https://www.postgresql.org/docs/",
    )
    assert mat_link.id is not None
    assert mat_link.link_url == "https://www.postgresql.org/docs/"


@pytest.mark.django_db
def test_faculty_can_create_scheduled_material():
    course = Course.objects.create(code="CS301", title="Database Systems")
    CourseMembership.objects.create(course=course, user_id=9001, role=CourseRole.FACULTY)

    faculty = make_principal(
        9001, "faculty", ("lms.course.view", "lms.material.manage")
    )

    future_release = datetime.now(UTC) + timedelta(days=7)
    mat = material_service.create_course_material(
        actor=faculty,
        course_code="CS301",
        title="Midterm Review Sheet",
        section_title="Week 6: Midterm Exam Prep",
        section_type=SectionType.WEEK,
        material_type=MaterialType.NOTE,
        status=MaterialStatus.SCHEDULED,
        release_at=future_release,
        content="Midterm study guide and formula sheet.",
    )
    assert mat.status == MaterialStatus.SCHEDULED
    assert mat.release_at == future_release


@pytest.mark.django_db
def test_ta_cannot_create_or_modify_materials():
    course = Course.objects.create(code="CS301", title="Database Systems")
    CourseMembership.objects.create(course=course, user_id=2001, role=CourseRole.TA)

    ta = make_principal(2001, "staff", ("lms.course.view", "lms.material.manage"))

    with pytest.raises(PermissionDeniedError, match="Only faculty assigned"):
        material_service.create_course_material(
            actor=ta,
            course_code="CS301",
            title="TA Note",
            section_title="Week 1",
            material_type=MaterialType.NOTE,
            content="TA lab guide",
        )


@pytest.mark.django_db
def test_student_and_observer_cannot_create_materials():
    course = Course.objects.create(code="CS301", title="Database Systems")
    CourseMembership.objects.create(course=course, user_id=1001, role=CourseRole.STUDENT)
    CourseMembership.objects.create(course=course, user_id=3001, role=CourseRole.OBSERVER)

    student = make_principal(1001, "student", ("lms.course.view", "lms.material.manage"))
    observer = make_principal(3001, "staff", ("lms.course.view", "lms.material.manage"))

    with pytest.raises(PermissionDeniedError, match="Only faculty assigned"):
        material_service.create_course_material(
            actor=student,
            course_code="CS301",
            title="Student upload",
            section_title="Week 1",
            material_type=MaterialType.NOTE,
            content="Text",
        )

    with pytest.raises(PermissionDeniedError, match="Only faculty assigned"):
        material_service.create_course_material(
            actor=observer,
            course_code="CS301",
            title="Observer upload",
            section_title="Week 1",
            material_type=MaterialType.NOTE,
            content="Text",
        )


@pytest.mark.django_db
def test_faculty_can_update_and_delete_material():
    course = Course.objects.create(code="CS301", title="Database Systems")
    CourseMembership.objects.create(course=course, user_id=9001, role=CourseRole.FACULTY)

    faculty = make_principal(
        9001, "faculty", ("lms.course.view", "lms.material.manage")
    )

    mat = material_service.create_course_material(
        actor=faculty,
        course_code="CS301",
        title="Draft Chapter",
        section_title="Module 1",
        material_type=MaterialType.NOTE,
        status=MaterialStatus.DRAFT,
        content="Draft text",
    )

    updated = material_service.update_course_material(
        actor=faculty,
        course_code="CS301",
        material_id=mat.id,
        title="Final Chapter 1 Notes",
        status=MaterialStatus.PUBLISHED,
        content="Polished text ready for students.",
    )
    assert updated.title == "Final Chapter 1 Notes"
    assert updated.status == MaterialStatus.PUBLISHED

    material_service.delete_course_material(
        actor=faculty,
        course_code="CS301",
        material_id=mat.id,
    )
    assert not CourseMaterial.objects.filter(id=mat.id).exists()


@pytest.mark.django_db
def test_release_scheduled_materials_transition():
    course = Course.objects.create(code="CS301", title="Database Systems")

    past_release = datetime.now(UTC) - timedelta(hours=2)
    future_release = datetime.now(UTC) + timedelta(days=5)

    m1 = CourseMaterial.objects.create(
        course=course,
        title="Scheduled Due for Release",
        section_title="Module 1",
        material_type=MaterialType.NOTE,
        status=MaterialStatus.SCHEDULED,
        release_at=past_release,
        content="Now active",
        created_by_user_id=9001,
    )
    m2 = CourseMaterial.objects.create(
        course=course,
        title="Still Future Material",
        section_title="Module 2",
        material_type=MaterialType.NOTE,
        status=MaterialStatus.SCHEDULED,
        release_at=future_release,
        content="Not yet",
        created_by_user_id=9001,
    )

    count = material_service.release_scheduled_materials()
    assert count == 1

    m1.refresh_from_db()
    m2.refresh_from_db()
    assert m1.status == MaterialStatus.PUBLISHED
    assert m2.status == MaterialStatus.SCHEDULED


@pytest.mark.django_db
def test_faculty_can_post_announcement_timestamped():
    course = Course.objects.create(
        code="CS501",
        title="Advanced Algorithms",
        status=CourseStatus.PUBLISHED,
    )
    CourseMembership.objects.create(course=course, user_id=101, role=CourseRole.FACULTY)

    faculty = make_principal(101, "faculty", ("lms.announcement.manage", "lms.announcement.view"))
    announcement = announcement_service.post_course_announcement(
        actor=faculty,
        course_code="CS501",
        title="Midterm Exam Schedule",
        content="Exam will be held next Monday at 10 AM in Hall A.",
    )

    assert announcement.id is not None
    assert announcement.title == "Midterm Exam Schedule"
    assert announcement.content == "Exam will be held next Monday at 10 AM in Hall A."
    assert announcement.created_by_user_id == 101
    assert announcement.author_role == CourseRole.FACULTY
    assert announcement.created_at is not None  # Timestamped (AFR-LMS-005.3, BR-LMS-008)


@pytest.mark.django_db
def test_unauthorized_roles_cannot_post_announcement():
    course = Course.objects.create(
        code="CS502",
        title="Operating Systems",
        status=CourseStatus.PUBLISHED,
    )
    CourseMembership.objects.create(course=course, user_id=201, role=CourseRole.STUDENT)
    CourseMembership.objects.create(course=course, user_id=202, role=CourseRole.TA)
    CourseMembership.objects.create(course=course, user_id=203, role=CourseRole.OBSERVER)

    student = make_principal(201, "student", ("lms.announcement.manage", "lms.announcement.view"))
    ta = make_principal(202, "ta", ("lms.announcement.manage", "lms.announcement.view"))
    observer = make_principal(203, "observer", ("lms.announcement.manage", "lms.announcement.view"))

    # Student cannot post (BR-LMS-007)
    with pytest.raises(PermissionDeniedError, match="Students cannot post course announcements"):
        announcement_service.post_course_announcement(
            actor=student,
            course_code="CS502",
            title="Student Announcement",
            content="Testing unauthorized post",
        )

    # TA cannot post without permitted mechanism (AFR-LMS-005.2, AFR-LMS-014.2, BR-LMS-007)
    with pytest.raises(
        PermissionDeniedError, match="Teaching Assistants are not permitted to post announcements"
    ):
        announcement_service.post_course_announcement(
            actor=ta,
            course_code="CS502",
            title="TA Announcement",
            content="Testing TA post",
        )

    # Observer has read-only access (AFR-LMS-015.4)
    with pytest.raises(
        PermissionDeniedError, match="Observers have read-only access and cannot post announcements"
    ):
        announcement_service.post_course_announcement(
            actor=observer,
            course_code="CS502",
            title="Observer Announcement",
            content="Testing observer post",
        )


@pytest.mark.django_db
def test_non_member_cannot_post_or_view_announcements():
    course = Course.objects.create(
        code="CS503",
        title="Computer Networks",
        status=CourseStatus.PUBLISHED,
    )
    CourseMembership.objects.create(course=course, user_id=301, role=CourseRole.FACULTY)

    non_member = make_principal(999, "faculty", ("lms.announcement.manage", "lms.announcement.view"))

    with pytest.raises(NotFoundError, match="Course not found or you are not linked to it"):
        announcement_service.post_course_announcement(
            actor=non_member,
            course_code="CS503",
            title="Intruder Announcement",
            content="Should fail",
        )

    # Selectors return None for non-members (BR-LMS-001)
    assert list_course_announcements(principal=non_member, course_code="CS503") is None
    assert (
        get_course_announcement_detail(principal=non_member, course_code="CS503", announcement_id=1)
        is None
    )


@pytest.mark.django_db
def test_all_enrolled_and_linked_users_can_view_course_announcements():
    course = Course.objects.create(
        code="CS504",
        title="Software Engineering",
        status=CourseStatus.PUBLISHED,
    )
    CourseMembership.objects.create(course=course, user_id=401, role=CourseRole.FACULTY)
    CourseMembership.objects.create(course=course, user_id=402, role=CourseRole.STUDENT)
    CourseMembership.objects.create(course=course, user_id=403, role=CourseRole.TA)
    CourseMembership.objects.create(course=course, user_id=404, role=CourseRole.OBSERVER)

    ann = CourseAnnouncement.objects.create(
        course=course,
        title="Project Milestone 1 Due",
        content="Submit your milestone reports before Sunday midnight.",
        created_by_user_id=401,
        author_role=CourseRole.FACULTY,
    )

    faculty = make_principal(401, "faculty", ("lms.announcement.view", "lms.announcement.manage"))
    student = make_principal(402, "student", ("lms.announcement.view",))
    ta = make_principal(403, "ta", ("lms.announcement.view",))
    observer = make_principal(404, "observer", ("lms.announcement.view",))

    for actor, expected_can_post in [
        (faculty, True),
        (student, False),
        (ta, False),
        (observer, False),
    ]:
        data = list_course_announcements(principal=actor, course_code="CS504")
        assert data is not None
        assert data["course_code"] == "CS504"
        assert data["can_post"] is expected_can_post
        assert len(data["announcements"]) == 1
        assert data["announcements"][0]["title"] == "Project Milestone 1 Due"
        assert data["announcements"][0]["created_at"] is not None

        detail = get_course_announcement_detail(
            principal=actor, course_code="CS504", announcement_id=ann.id
        )
        assert detail is not None
        assert detail["title"] == "Project Milestone 1 Due"


@pytest.mark.django_db
def test_contract_get_course_announcements():
    c1 = Course.objects.create(code="CS505A", title="Course A", status=CourseStatus.PUBLISHED)
    c2 = Course.objects.create(code="CS505B", title="Course B", status=CourseStatus.PUBLISHED)

    CourseAnnouncement.objects.create(
        course=c1, title="A1", content="Content A1", created_by_user_id=1, author_role="faculty"
    )
    CourseAnnouncement.objects.create(
        course=c2, title="B1", content="Content B1", created_by_user_id=1, author_role="faculty"
    )

    res = get_course_announcements(["CS505A", "CS505B", "NONEXISTENT"])
    assert "CS505A" in res
    assert "CS505B" in res
    assert "NONEXISTENT" in res
    assert len(res["CS505A"]) == 1
    assert res["CS505A"][0]["title"] == "A1"
    assert len(res["CS505B"]) == 1
    assert res["CS505B"][0]["title"] == "B1"
    assert len(res["NONEXISTENT"]) == 0


@pytest.mark.django_db
def test_faculty_can_create_draft_assignment():
    course = Course.objects.create(code="CS601", title="Algorithms", status=CourseStatus.PUBLISHED)
    CourseMembership.objects.create(course=course, user_id=101, role=CourseRole.FACULTY)
    faculty = make_principal(101, "faculty", ("lms.assignment.view", "lms.assignment.manage"))

    asg = assignment_service.create_course_assignment(
        actor=faculty,
        course_code="CS601",
        title="Divide and Conquer",
        submission_type=SubmissionType.FILE,
        points_possible=100,
        status=AssignmentStatus.DRAFT,
    )

    assert asg.id is not None
    assert asg.title == "Divide and Conquer"
    assert asg.status == AssignmentStatus.DRAFT
    assert asg.submission_type == "file"
    assert asg.points_possible == Decimal("100.00")
    assert asg.created_by_user_id == 101


@pytest.mark.django_db
def test_faculty_can_create_and_publish_assignment():
    course = Course.objects.create(code="CS602", title="Networking", status=CourseStatus.PUBLISHED)
    CourseMembership.objects.create(course=course, user_id=101, role=CourseRole.FACULTY)
    faculty = make_principal(101, "faculty", ("lms.assignment.view", "lms.assignment.manage"))

    now = datetime.now(UTC)
    due = now + timedelta(days=7)

    asg = assignment_service.create_course_assignment(
        actor=faculty,
        course_code="CS602",
        title="Socket Programming",
        instructions="Implement TCP client and server in Python.",
        submission_type=SubmissionType.FILE,
        points_possible=50,
        status=AssignmentStatus.PUBLISHED,
        due_at=due,
    )

    assert asg.status == AssignmentStatus.PUBLISHED
    assert asg.instructions == "Implement TCP client and server in Python."


@pytest.mark.django_db
def test_faculty_can_edit_assignment():
    course = Course.objects.create(code="CS603", title="AI", status=CourseStatus.PUBLISHED)
    CourseMembership.objects.create(course=course, user_id=101, role=CourseRole.FACULTY)
    faculty = make_principal(101, "faculty", ("lms.assignment.view", "lms.assignment.manage"))

    asg = assignment_service.create_course_assignment(
        actor=faculty,
        course_code="CS603",
        title="Search Algorithms Draft",
        status=AssignmentStatus.DRAFT,
    )

    now = datetime.now(UTC)
    due = now + timedelta(days=5)

    updated = assignment_service.update_course_assignment(
        actor=faculty,
        course_code="CS603",
        assignment_id=asg.id,
        title="Search Algorithms Final",
        instructions="Implement A* search.",
        status=AssignmentStatus.PUBLISHED,
        due_at=due,
        points_possible=75,
    )

    assert updated.title == "Search Algorithms Final"
    assert updated.status == AssignmentStatus.PUBLISHED
    assert updated.instructions == "Implement A* search."
    assert updated.points_possible == Decimal("75.00")


@pytest.mark.django_db
def test_faculty_can_delete_assignment():
    course = Course.objects.create(code="CS604", title="Databases", status=CourseStatus.PUBLISHED)
    CourseMembership.objects.create(course=course, user_id=101, role=CourseRole.FACULTY)
    faculty = make_principal(101, "faculty", ("lms.assignment.view", "lms.assignment.manage"))

    asg = assignment_service.create_course_assignment(
        actor=faculty,
        course_code="CS604",
        title="To Be Deleted",
        status=AssignmentStatus.DRAFT,
    )

    assignment_service.delete_course_assignment(
        actor=faculty, course_code="CS604", assignment_id=asg.id
    )

    assert not CourseAssignment.objects.filter(id=asg.id).exists()


@pytest.mark.django_db
def test_ta_cannot_create_or_edit_assignments():
    course = Course.objects.create(code="CS605", title="OS", status=CourseStatus.PUBLISHED)
    CourseMembership.objects.create(course=course, user_id=201, role=CourseRole.TA)
    ta = make_principal(201, "ta", ("lms.assignment.view", "lms.assignment.manage"))

    # TA creation rejected
    with pytest.raises(PermissionDeniedError, match="Teaching Assistants are not permitted"):
        assignment_service.create_course_assignment(
            actor=ta,
            course_code="CS605",
            title="TA Assignment",
            status=AssignmentStatus.DRAFT,
        )

    # Pre-existing assignment created by faculty
    asg = CourseAssignment.objects.create(
        course=course,
        title="Kernel Modules",
        instructions="Instructions",
        submission_type="file",
        status=AssignmentStatus.DRAFT,
        created_by_user_id=101,
    )

    # TA edit rejected
    with pytest.raises(PermissionDeniedError, match="Teaching Assistants are not permitted"):
        assignment_service.update_course_assignment(
            actor=ta,
            course_code="CS605",
            assignment_id=asg.id,
            title="TA Edited",
        )


@pytest.mark.django_db
def test_student_and_observer_cannot_author_assignments():
    course = Course.objects.create(code="CS606", title="Compilers", status=CourseStatus.PUBLISHED)
    CourseMembership.objects.create(course=course, user_id=301, role=CourseRole.STUDENT)
    CourseMembership.objects.create(course=course, user_id=302, role=CourseRole.OBSERVER)

    student = make_principal(301, "student", ("lms.assignment.view", "lms.assignment.manage"))
    observer = make_principal(302, "observer", ("lms.assignment.view", "lms.assignment.manage"))

    with pytest.raises(PermissionDeniedError, match="Students cannot create"):
        assignment_service.create_course_assignment(
            actor=student,
            course_code="CS606",
            title="Student Assignment",
        )

    with pytest.raises(PermissionDeniedError, match="Observers have read-only"):
        assignment_service.create_course_assignment(
            actor=observer,
            course_code="CS606",
            title="Observer Assignment",
        )


@pytest.mark.django_db
def test_student_cannot_view_draft_or_unreleased_scheduled_assignments():
    course = Course.objects.create(code="CS607", title="Security", status=CourseStatus.PUBLISHED)
    CourseMembership.objects.create(course=course, user_id=101, role=CourseRole.FACULTY)
    CourseMembership.objects.create(course=course, user_id=401, role=CourseRole.STUDENT)

    now = datetime.now(UTC)
    future_release = now + timedelta(days=2)
    due = now + timedelta(days=7)

    # 1. Draft assignment
    draft = CourseAssignment.objects.create(
        course=course,
        title="Draft Exam",
        instructions="Hidden draft",
        status=AssignmentStatus.DRAFT,
        created_by_user_id=101,
    )

    # 2. Future-scheduled assignment
    scheduled = CourseAssignment.objects.create(
        course=course,
        title="Scheduled Crypto",
        instructions="Hidden future assignment",
        status=AssignmentStatus.SCHEDULED,
        release_at=future_release,
        due_at=due,
        created_by_user_id=101,
    )

    # 3. Published available assignment
    published = CourseAssignment.objects.create(
        course=course,
        title="Available Lab 1",
        instructions="Buffer overflow lab",
        status=AssignmentStatus.PUBLISHED,
        due_at=due,
        created_by_user_id=101,
    )

    student = make_principal(401, "student", ("lms.assignment.view",))
    data = list_course_assignments(principal=student, course_code="CS607")

    assert data is not None
    assert data["can_manage"] is False
    assert len(data["assignments"]) == 1
    assert data["assignments"][0]["id"] == published.id
    assert data["assignments"][0]["title"] == "Available Lab 1"

    # Detail check: draft and scheduled should return None for student
    assert get_course_assignment_detail(
        principal=student, course_code="CS607", assignment_id=draft.id
    ) is None
    assert get_course_assignment_detail(
        principal=student, course_code="CS607", assignment_id=scheduled.id
    ) is None

    # Published detail works
    pub_detail = get_course_assignment_detail(
        principal=student, course_code="CS607", assignment_id=published.id
    )
    assert pub_detail is not None
    assert pub_detail["title"] == "Available Lab 1"


@pytest.mark.django_db
def test_release_scheduled_assignments():
    course = Course.objects.create(code="CS608", title="Networks", status=CourseStatus.PUBLISHED)
    past = datetime.now(UTC) - timedelta(hours=1)
    future = datetime.now(UTC) + timedelta(hours=2)

    # Ready for release
    asg_ready = CourseAssignment.objects.create(
        course=course,
        title="Ready to Release",
        instructions="Instructions",
        status=AssignmentStatus.SCHEDULED,
        release_at=past,
        created_by_user_id=1,
    )

    # Not ready for release
    asg_not_ready = CourseAssignment.objects.create(
        course=course,
        title="Not Ready",
        instructions="Instructions",
        status=AssignmentStatus.SCHEDULED,
        release_at=future,
        created_by_user_id=1,
    )

    count = assignment_service.release_scheduled_assignments()
    assert count == 1

    asg_ready.refresh_from_db()
    asg_not_ready.refresh_from_db()

    assert asg_ready.status == AssignmentStatus.PUBLISHED
    assert asg_not_ready.status == AssignmentStatus.SCHEDULED


@pytest.mark.django_db
def test_contract_get_course_assignments():
    c1 = Course.objects.create(code="CS609A", title="Course A", status=CourseStatus.PUBLISHED)
    c2 = Course.objects.create(code="CS609B", title="Course B", status=CourseStatus.PUBLISHED)

    CourseAssignment.objects.create(
        course=c1,
        title="A1",
        instructions="Ins A1",
        status=AssignmentStatus.PUBLISHED,
        created_by_user_id=1,
    )
    CourseAssignment.objects.create(
        course=c2,
        title="B1",
        instructions="Ins B1",
        status=AssignmentStatus.PUBLISHED,
        created_by_user_id=1,
    )

    res = get_course_assignments(["CS609A", "CS609B", "NONEXISTENT"])
    assert "CS609A" in res
    assert "CS609B" in res
    assert "NONEXISTENT" in res
    assert len(res["CS609A"]) == 1
    assert res["CS609A"][0]["title"] == "A1"
    assert len(res["CS609B"]) == 1
    assert res["CS609B"][0]["title"] == "B1"
    assert len(res["NONEXISTENT"]) == 0


@pytest.mark.django_db
def test_update_assignment_window_faculty_success():
    course = Course.objects.create(code="CS701", title="Algorithms", status=CourseStatus.PUBLISHED)
    faculty_user_id = 10
    CourseMembership.objects.create(course=course, user_id=faculty_user_id, role=CourseRole.FACULTY)

    now = datetime.now(UTC)
    due = now + timedelta(days=4)
    closes = now + timedelta(days=7)

    asg = CourseAssignment.objects.create(
        course=course,
        title="Dynamic Programming",
        instructions="Solve knapsack",
        status=AssignmentStatus.PUBLISHED,
        created_by_user_id=faculty_user_id,
        due_at=due,
    )

    faculty = make_principal(
        user_id=faculty_user_id,
        role="faculty",
        permissions=("lms.course.view", "lms.assignment.manage", "lms.deadline.manage"),
    )

    info = deadline_service.update_assignment_window(
        actor=faculty,
        course_code="CS701",
        assignment_id=asg.id,
        due_at=due,
        closes_at=closes,
        allow_late=True,
    )

    assert info.closes_at == closes
    assert info.allow_late is True
    assert calculate_deadline_info(info)["window_status"] == DeadlineWindowStatus.OPEN

    asg.refresh_from_db()
    assert asg.closes_at == closes
    assert asg.allow_late is True


@pytest.mark.django_db
def test_update_assignment_window_permission_denied_for_ta_and_student():
    course = Course.objects.create(code="CS702", title="AI", status=CourseStatus.PUBLISHED)
    CourseMembership.objects.create(course=course, user_id=11, role=CourseRole.TA)
    CourseMembership.objects.create(course=course, user_id=12, role=CourseRole.STUDENT)

    asg = CourseAssignment.objects.create(
        course=course,
        title="Search Trees",
        instructions="Solve search",
        status=AssignmentStatus.PUBLISHED,
        created_by_user_id=1,
    )

    ta = make_principal(
        user_id=11,
        role="ta",
        permissions=("lms.course.view", "lms.deadline.view"),
    )
    student = make_principal(
        user_id=12,
        role="student",
        permissions=("lms.course.view", "lms.deadline.view"),
    )

    with pytest.raises(PermissionDeniedError):
        deadline_service.update_assignment_window(
            actor=ta,
            course_code="CS702",
            assignment_id=asg.id,
            allow_late=True,
        )

    with pytest.raises(PermissionDeniedError):
        deadline_service.update_assignment_window(
            actor=student,
            course_code="CS702",
            assignment_id=asg.id,
            allow_late=True,
        )


@pytest.mark.django_db
def test_grant_and_revoke_assignment_extension():
    course = Course.objects.create(code="CS703", title="Networks", status=CourseStatus.PUBLISHED)
    faculty_user_id = 20
    student_user_id = 30
    unenrolled_student_id = 99

    CourseMembership.objects.create(course=course, user_id=faculty_user_id, role=CourseRole.FACULTY)
    CourseMembership.objects.create(course=course, user_id=student_user_id, role=CourseRole.STUDENT)

    now = datetime.now(UTC)
    due = now + timedelta(days=2)
    ext_due = now + timedelta(days=5)

    asg = CourseAssignment.objects.create(
        course=course,
        title="Routing Protocols",
        instructions="Implement Dijkstra",
        status=AssignmentStatus.PUBLISHED,
        created_by_user_id=faculty_user_id,
        due_at=due,
    )

    faculty = make_principal(
        user_id=faculty_user_id,
        role="faculty",
        permissions=("lms.course.view", "lms.assignment.manage", "lms.deadline.manage"),
    )

    # 1. Unenrolled student cannot receive extension
    with pytest.raises(ConflictError, match="not an enrolled student"):
        deadline_service.grant_assignment_extension(
            actor=faculty,
            course_code="CS703",
            assignment_id=asg.id,
            student_user_id=unenrolled_student_id,
            extended_due_at=ext_due,
            reason="Accommodation",
        )

    # 2. Enrolled student receives extension
    ext = deadline_service.grant_assignment_extension(
        actor=faculty,
        course_code="CS703",
        assignment_id=asg.id,
        student_user_id=student_user_id,
        extended_due_at=ext_due,
        reason="Medical accommodation",
    )
    assert ext.user_id == student_user_id
    assert ext.extended_due_at == ext_due
    assert ext.reason == "Medical accommodation"
    assert ext.granted_by_user_id == faculty_user_id

    # 3. Revoke extension
    deadline_service.revoke_assignment_extension(
        actor=faculty,
        course_code="CS703",
        assignment_id=asg.id,
        extension_id=ext.id,
    )
    assert CourseAssignmentExtension.objects.filter(id=ext.id).count() == 0


@pytest.mark.django_db
def test_student_extension_privacy_and_effective_deadline():
    course = Course.objects.create(code="CS704", title="OS", status=CourseStatus.PUBLISHED)
    faculty_user_id = 40
    student1_user_id = 41
    student2_user_id = 42
    ta_user_id = 43

    CourseMembership.objects.create(course=course, user_id=faculty_user_id, role=CourseRole.FACULTY)
    CourseMembership.objects.create(course=course, user_id=student1_user_id, role=CourseRole.STUDENT)
    CourseMembership.objects.create(course=course, user_id=student2_user_id, role=CourseRole.STUDENT)
    CourseMembership.objects.create(course=course, user_id=ta_user_id, role=CourseRole.TA)

    now = datetime.now(UTC)
    due = now + timedelta(days=3)
    ext_due = now + timedelta(days=6)

    asg = CourseAssignment.objects.create(
        course=course,
        title="Threads & Locks",
        instructions="Implement mutex",
        status=AssignmentStatus.PUBLISHED,
        created_by_user_id=faculty_user_id,
        due_at=due,
    )

    # Grant extension ONLY to student 1
    CourseAssignmentExtension.objects.create(
        assignment=asg,
        user_id=student1_user_id,
        extended_due_at=ext_due,
        reason="Dean approved leave",
        granted_by_user_id=faculty_user_id,
    )

    s1_principal = make_principal(
        user_id=student1_user_id,
        role="student",
        permissions=("lms.course.view", "lms.deadline.view"),
    )
    s2_principal = make_principal(
        user_id=student2_user_id,
        role="student",
        permissions=("lms.course.view", "lms.deadline.view"),
    )
    ta_principal = make_principal(
        user_id=ta_user_id,
        role="ta",
        permissions=("lms.course.view", "lms.deadline.view"),
    )

    # Student 1 sees their personal extension and effective deadline
    info1 = get_assignment_deadline_info(
        principal=s1_principal,
        course_code="CS704",
        assignment_id=asg.id,
    )
    assert info1["is_extended"] is True
    assert info1["extended_due_at"] is not None
    assert info1["extension_reason"] == "Dean approved leave"

    # Student 2 cannot see student 1's extension (strict privacy)
    info2 = get_assignment_deadline_info(
        principal=s2_principal,
        course_code="CS704",
        assignment_id=asg.id,
    )
    assert info2["is_extended"] is False
    assert info2["extended_due_at"] is None
    assert info2["extension_reason"] == ""

    # Student cannot list extensions of peers (selector returns None for unauthorized roles)
    assert (
        list_assignment_extensions(
            principal=s1_principal,
            course_code="CS704",
            assignment_id=asg.id,
        )
        is None
    )

    # TA can list all extensions for grading context (AFR-LMS-014.2)
    ta_exts = list_assignment_extensions(
        principal=ta_principal,
        course_code="CS704",
        assignment_id=asg.id,
    )
    assert ta_exts is not None
    assert len(ta_exts) == 1
    assert ta_exts[0]["user_id"] == student1_user_id


@pytest.mark.django_db
def test_contract_get_assignment_deadlines():
    course = Course.objects.create(code="CS705", title="Security", status=CourseStatus.PUBLISHED)
    now = datetime.now(UTC)

    asg1 = CourseAssignment.objects.create(
        course=course,
        title="RSA",
        status=AssignmentStatus.PUBLISHED,
        created_by_user_id=1,
        due_at=now + timedelta(days=2),
    )
    asg2 = CourseAssignment.objects.create(
        course=course,
        title="AES",
        status=AssignmentStatus.PUBLISHED,
        created_by_user_id=1,
        due_at=now + timedelta(days=4),
        closes_at=now + timedelta(days=6),
        allow_late=True,
    )

    # Extension for student 55 on asg1
    CourseAssignmentExtension.objects.create(
        assignment=asg1,
        user_id=55,
        extended_due_at=now + timedelta(days=5),
        reason="Medical",
        granted_by_user_id=1,
    )

    deadlines = get_assignment_deadlines([asg1.id, asg2.id, 99999], student_user_id=55)
    assert asg1.id in deadlines
    assert asg2.id in deadlines
    assert 99999 not in deadlines

    assert deadlines[asg1.id]["is_extended"] is True
    assert deadlines[asg2.id]["is_extended"] is False
    assert deadlines[asg2.id]["allow_late"] is True


@pytest.mark.django_db
def test_submission_service_on_time_text_and_resubmission():
    from conftest import make_principal

    course = Course.objects.create(code="CS801", title="Compiler Design", status=CourseStatus.PUBLISHED)
    now = datetime.now(UTC)

    # Faculty, Student
    CourseMembership.objects.create(course=course, user_id=1, role=CourseRole.FACULTY)
    CourseMembership.objects.create(course=course, user_id=20, role=CourseRole.STUDENT)

    student_principal = make_principal(
        user_id=20,
        kind="student",
        roles=("student",),
        active_role="student",
        permissions=("lms.submission.submit", "lms.submission.view", "lms.assignment.view"),
        modules=("lms",),
    )

    asg = CourseAssignment.objects.create(
        course=course,
        title="Lexer Implementation",
        submission_type=SubmissionType.TEXT,
        status=AssignmentStatus.PUBLISHED,
        created_by_user_id=1,
        due_at=now + timedelta(days=3),
    )

    # 1. Initial on-time submission
    sub1 = submission_service.create_submission(
        actor=student_principal,
        course_code="CS801",
        assignment_id=asg.id,
        submission_type="text",
        content_text="def tokenize(s): return s.split()",
    )
    assert sub1.attempt_number == 1
    assert sub1.is_latest is True
    assert sub1.status == SubmissionStatus.SUBMITTED
    assert sub1.content_text == "def tokenize(s): return s.split()"

    # 2. Resubmission (attempt 2)
    sub2 = submission_service.create_submission(
        actor=student_principal,
        course_code="CS801",
        assignment_id=asg.id,
        submission_type="text",
        content_text="def tokenize_v2(s): import re; return re.findall(r'\\w+', s)",
    )
    assert sub2.attempt_number == 2
    assert sub2.is_latest is True
    assert sub2.status == SubmissionStatus.SUBMITTED

    # Check that previous submission is no longer latest
    sub1.refresh_from_db()
    assert sub1.is_latest is False

    # Check student history selector
    hist = get_student_submission_history(
        principal=student_principal,
        course_code="CS801",
        assignment_id=asg.id,
    )
    assert hist is not None
    assert hist["status"] == "submitted"
    assert hist["total_attempts"] == 2
    assert len(hist["history"]) == 2
    assert hist["history"][0]["attempt_number"] == 2
    assert hist["history"][1]["attempt_number"] == 1


@pytest.mark.django_db
def test_submission_service_file_and_download():
    from django.core.files.uploadedfile import SimpleUploadedFile

    from conftest import make_principal

    course = Course.objects.create(code="CS802", title="OS", status=CourseStatus.PUBLISHED)
    now = datetime.now(UTC)

    CourseMembership.objects.create(course=course, user_id=1, role=CourseRole.FACULTY)
    CourseMembership.objects.create(course=course, user_id=2, role=CourseRole.TA)
    CourseMembership.objects.create(course=course, user_id=30, role=CourseRole.STUDENT)
    CourseMembership.objects.create(course=course, user_id=31, role=CourseRole.STUDENT)
    CourseMembership.objects.create(course=course, user_id=40, role=CourseRole.OBSERVER)

    s1_principal = make_principal(
        user_id=30,
        kind="student",
        roles=("student",),
        active_role="student",
        permissions=("lms.submission.submit", "lms.submission.view", "lms.assignment.view"),
        modules=("lms",),
    )
    s2_principal = make_principal(
        user_id=31,
        kind="student",
        roles=("student",),
        active_role="student",
        permissions=("lms.submission.submit", "lms.submission.view", "lms.assignment.view"),
        modules=("lms",),
    )
    faculty_principal = make_principal(
        user_id=1,
        kind="faculty",
        roles=("faculty",),
        active_role="faculty",
        permissions=("lms.submission.view", "lms.assignment.view"),
        modules=("lms",),
    )
    ta_principal = make_principal(
        user_id=2,
        kind="ta",
        roles=("ta",),
        active_role="ta",
        permissions=("lms.submission.view", "lms.assignment.view"),
        modules=("lms",),
    )
    observer_principal = make_principal(
        user_id=40,
        kind="observer",
        roles=("observer",),
        active_role="observer",
        permissions=("lms.assignment.view",),
        modules=("lms",),
    )

    asg = CourseAssignment.objects.create(
        course=course,
        title="Kernel Patch",
        submission_type=SubmissionType.FILE,
        status=AssignmentStatus.PUBLISHED,
        created_by_user_id=1,
        due_at=now + timedelta(days=2),
    )

    uploaded_file = SimpleUploadedFile("patch.diff", b"diff --git a/main.c b/main.c\n+ok")
    sub = submission_service.create_submission(
        actor=s1_principal,
        course_code="CS802",
        assignment_id=asg.id,
        submission_type="file",
        file=uploaded_file,
    )
    assert sub.submission_type == "file"
    assert sub.file_name == "patch.diff"
    assert sub.file_size is not None

    # Student 1 can download own file
    d1 = get_submission_for_download(
        principal=s1_principal,
        course_code="CS802",
        assignment_id=asg.id,
        submission_id=sub.id,
    )
    assert d1 is not None
    assert d1.id == sub.id

    # Student 2 cannot download Student 1's file (privacy enforcement, BR-LMS-014)
    d2 = get_submission_for_download(
        principal=s2_principal,
        course_code="CS802",
        assignment_id=asg.id,
        submission_id=sub.id,
    )
    assert d2 is None

    # Faculty can download
    d_fac = get_submission_for_download(
        principal=faculty_principal,
        course_code="CS802",
        assignment_id=asg.id,
        submission_id=sub.id,
    )
    assert d_fac is not None

    # TA can download
    d_ta = get_submission_for_download(
        principal=ta_principal,
        course_code="CS802",
        assignment_id=asg.id,
        submission_id=sub.id,
    )
    assert d_ta is not None

    # Observer cannot download
    d_obs = get_submission_for_download(
        principal=observer_principal,
        course_code="CS802",
        assignment_id=asg.id,
        submission_id=sub.id,
    )
    assert d_obs is None


@pytest.mark.django_db
def test_submission_service_link_and_type_mismatch():
    from conftest import make_principal

    course = Course.objects.create(code="CS803", title="Web Dev", status=CourseStatus.PUBLISHED)
    now = datetime.now(UTC)

    CourseMembership.objects.create(course=course, user_id=1, role=CourseRole.FACULTY)
    CourseMembership.objects.create(course=course, user_id=50, role=CourseRole.STUDENT)

    student_principal = make_principal(
        user_id=50,
        kind="student",
        roles=("student",),
        active_role="student",
        permissions=("lms.submission.submit", "lms.submission.view", "lms.assignment.view"),
        modules=("lms",),
    )

    asg = CourseAssignment.objects.create(
        course=course,
        title="Portfolio Site",
        submission_type=SubmissionType.LINK,
        status=AssignmentStatus.PUBLISHED,
        created_by_user_id=1,
        due_at=now + timedelta(days=5),
    )

    # Valid link submission
    sub = submission_service.create_submission(
        actor=student_principal,
        course_code="CS803",
        assignment_id=asg.id,
        submission_type="link",
        link_url="https://student-portfolio.example.com",
    )
    assert sub.submission_type == "link"
    assert sub.link_url == "https://student-portfolio.example.com"

    # Type mismatch rejected
    with pytest.raises(ConflictError, match="does not match"):
        submission_service.create_submission(
            actor=student_principal,
            course_code="CS803",
            assignment_id=asg.id,
            submission_type="text",
            content_text="my link is inside text",
        )


@pytest.mark.django_db
def test_submission_service_late_and_closed_deadlines():
    from conftest import make_principal

    course = Course.objects.create(code="CS804", title="Algorithms", status=CourseStatus.PUBLISHED)
    now = datetime.now(UTC)

    CourseMembership.objects.create(course=course, user_id=1, role=CourseRole.FACULTY)
    CourseMembership.objects.create(course=course, user_id=60, role=CourseRole.STUDENT)

    student_principal = make_principal(
        user_id=60,
        kind="student",
        roles=("student",),
        active_role="student",
        permissions=("lms.submission.submit", "lms.submission.view", "lms.assignment.view"),
        modules=("lms",),
    )

    # 1. Assignment with late allowed: past due but before closes_at
    asg_late = CourseAssignment.objects.create(
        course=course,
        title="Sorting",
        submission_type=SubmissionType.TEXT,
        status=AssignmentStatus.PUBLISHED,
        created_by_user_id=1,
        due_at=now - timedelta(hours=2),
        closes_at=now + timedelta(days=2),
        allow_late=True,
    )
    sub_late = submission_service.create_submission(
        actor=student_principal,
        course_code="CS804",
        assignment_id=asg_late.id,
        submission_type="text",
        content_text="quicksort code",
    )
    assert sub_late.status == SubmissionStatus.LATE

    # 2. Assignment strictly past deadline: no late allowed
    asg_closed = CourseAssignment.objects.create(
        course=course,
        title="Graphs",
        submission_type=SubmissionType.TEXT,
        status=AssignmentStatus.PUBLISHED,
        created_by_user_id=1,
        due_at=now - timedelta(hours=1),
        allow_late=False,
    )
    with pytest.raises(ConflictError, match="Submission deadline window is closed"):
        submission_service.create_submission(
            actor=student_principal,
            course_code="CS804",
            assignment_id=asg_closed.id,
            submission_type="text",
            content_text="dijkstra code",
        )


@pytest.mark.django_db
def test_submission_service_extension_overrides_late():
    from conftest import make_principal

    course = Course.objects.create(code="CS805", title="Networks", status=CourseStatus.PUBLISHED)
    now = datetime.now(UTC)

    CourseMembership.objects.create(course=course, user_id=1, role=CourseRole.FACULTY)
    CourseMembership.objects.create(course=course, user_id=70, role=CourseRole.STUDENT)

    student_principal = make_principal(
        user_id=70,
        kind="student",
        roles=("student",),
        active_role="student",
        permissions=("lms.submission.submit", "lms.submission.view", "lms.assignment.view"),
        modules=("lms",),
    )

    asg = CourseAssignment.objects.create(
        course=course,
        title="Socket Lab",
        submission_type=SubmissionType.TEXT,
        status=AssignmentStatus.PUBLISHED,
        created_by_user_id=1,
        due_at=now - timedelta(hours=5),
        closes_at=now + timedelta(days=2),
        allow_late=True,
    )

    # Student 70 has an approved extension in the future
    CourseAssignmentExtension.objects.create(
        assignment=asg,
        user_id=70,
        extended_due_at=now + timedelta(days=1),
        reason="Medical emergency",
        granted_by_user_id=1,
    )

    # Submission should be SUBMITTED (on-time), not LATE, because effective_due_at is extended
    sub = submission_service.create_submission(
        actor=student_principal,
        course_code="CS805",
        assignment_id=asg.id,
        submission_type="text",
        content_text="import socket",
    )
    assert sub.status == SubmissionStatus.SUBMITTED


@pytest.mark.django_db
def test_submission_service_access_control():
    from conftest import make_principal

    course = Course.objects.create(code="CS806", title="AI", status=CourseStatus.PUBLISHED)
    now = datetime.now(UTC)

    CourseMembership.objects.create(course=course, user_id=1, role=CourseRole.FACULTY)
    CourseMembership.objects.create(course=course, user_id=2, role=CourseRole.TA)
    CourseMembership.objects.create(course=course, user_id=80, role=CourseRole.STUDENT)
    CourseMembership.objects.create(course=course, user_id=90, role=CourseRole.OBSERVER)

    observer_principal = make_principal(
        user_id=90,
        kind="observer",
        roles=("observer",),
        active_role="observer",
        permissions=("lms.submission.submit", "lms.submission.view", "lms.assignment.view"),
        modules=("lms",),
    )
    student_principal = make_principal(
        user_id=80,
        kind="student",
        roles=("student",),
        active_role="student",
        permissions=("lms.submission.submit", "lms.submission.view", "lms.assignment.view"),
        modules=("lms",),
    )
    faculty_principal = make_principal(
        user_id=1,
        kind="faculty",
        roles=("faculty",),
        active_role="faculty",
        permissions=("lms.submission.view", "lms.assignment.view"),
        modules=("lms",),
    )

    asg = CourseAssignment.objects.create(
        course=course,
        title="Search Lab",
        submission_type=SubmissionType.TEXT,
        status=AssignmentStatus.PUBLISHED,
        created_by_user_id=1,
        due_at=now + timedelta(days=2),
    )

    # Observer cannot submit (403 PermissionDeniedError)
    with pytest.raises(PermissionDeniedError, match="Only enrolled students can submit"):
        submission_service.create_submission(
            actor=observer_principal,
            course_code="CS806",
            assignment_id=asg.id,
            submission_type="text",
            content_text="observer text",
        )

    # Student cannot view all submissions (returns None)
    assert (
        list_assignment_submissions(
            principal=student_principal,
            course_code="CS806",
            assignment_id=asg.id,
        )
        is None
    )

    # Faculty can view submissions
    subs_list = list_assignment_submissions(
        principal=faculty_principal,
        course_code="CS806",
        assignment_id=asg.id,
    )
    assert subs_list is not None
    assert subs_list["assignment_id"] == asg.id


@pytest.mark.django_db
def test_contract_get_assignment_submissions():
    course = Course.objects.create(code="CS807", title="Math", status=CourseStatus.PUBLISHED)
    now = datetime.now(UTC)

    asg = CourseAssignment.objects.create(
        course=course,
        title="Linear Algebra",
        submission_type=SubmissionType.TEXT,
        status=AssignmentStatus.PUBLISHED,
        created_by_user_id=1,
        due_at=now + timedelta(days=1),
    )

    CourseSubmission.objects.create(
        assignment=asg,
        student_user_id=100,
        submission_type="text",
        status="submitted",
        submitted_at=now,
        content_text="Matrix solutions",
        attempt_number=1,
        is_latest=True,
    )

    results = get_assignment_submissions([asg.id, 99999], student_user_id=100)
    assert asg.id in results
    assert results[99999] == []
    assert results[asg.id][0]["attempt_number"] == 1
    assert results[asg.id][0]["status"] == "submitted"
