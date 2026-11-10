"""Integration tests for LMS Course Workspace and Materials services."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from fusion_auth.principal import Principal
from modules.lms.contracts import get_course_announcements, get_course_assignments
from modules.lms.domain.entities import (
    AssignmentStatus,
    CourseRole,
    CourseStatus,
    MaterialStatus,
    MaterialType,
    SectionType,
    SubmissionType,
)
from modules.lms.models import (
    Course,
    CourseAnnouncement,
    CourseAssignment,
    CourseMaterial,
    CourseMembership,
)
from modules.lms.selectors.announcements import (
    get_course_announcement_detail,
    list_course_announcements,
)
from modules.lms.selectors.assignments import (
    get_course_assignment_detail,
    list_course_assignments,
)
from modules.lms.services import announcements as announcement_service
from modules.lms.services import assignments as assignment_service
from modules.lms.services import courses as course_service
from modules.lms.services import materials as material_service


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
