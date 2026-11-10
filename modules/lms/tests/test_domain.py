"""Unit tests for LMS pure domain rules and entities."""
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from modules.lms.domain.entities import (
    AnnouncementDetails,
    AssignmentDetails,
    AssignmentStatus,
    CourseDetails,
    CourseRole,
    CourseStatus,
    MaterialDetails,
    MaterialStatus,
    MaterialType,
    SectionType,
    SubmissionType,
    validate_announcement_details,
    validate_assignment_details,
    validate_course_details,
    validate_material_details,
)
from modules.lms.domain.errors import (
    AssignmentAccessDeniedError,
    AssignmentAuthoringDeniedError,
    CourseAccessDeniedError,
    CourseEditingDeniedError,
    LMSRuleError,
    MaterialAccessDeniedError,
    MaterialAuthoringDeniedError,
)


def test_course_details_dataclass():
    c = CourseDetails(
        code="CS301",
        title="Database Systems",
        description="Core DBMS",
        syllabus="SQL, Relational Algebra",
        schedule="Mon/Wed 10:00-11:00",
        status=CourseStatus.PUBLISHED,
    )
    assert c.code == "CS301"
    assert c.title == "Database Systems"
    assert c.status == CourseStatus.PUBLISHED


def test_validate_course_details_valid():
    validate_course_details(title="Operating Systems", status=CourseStatus.PUBLISHED)
    validate_course_details(title="Compiler Design", status=CourseStatus.DRAFT)


def test_validate_course_details_empty_title():
    with pytest.raises(LMSRuleError, match="title cannot be empty"):
        validate_course_details(title="   ", status=CourseStatus.PUBLISHED)


def test_validate_course_details_title_too_long():
    with pytest.raises(LMSRuleError, match="exceed 200 characters"):
        validate_course_details(title="A" * 201, status=CourseStatus.PUBLISHED)


def test_validate_course_details_invalid_status():
    with pytest.raises(LMSRuleError, match="Invalid course status"):
        validate_course_details(title="Algorithms", status="archived")


def test_course_roles_and_privileges():
    assert CourseRole.FACULTY in CourseRole.EDITORS
    assert CourseRole.TA in CourseRole.READ_ONLY
    assert CourseRole.STUDENT in CourseRole.READ_ONLY
    assert CourseRole.OBSERVER in CourseRole.READ_ONLY
    assert CourseRole.TA not in CourseRole.EDITORS
    assert CourseRole.OBSERVER not in CourseRole.EDITORS


def test_lms_error_hierarchy():
    assert issubclass(CourseAccessDeniedError, LMSRuleError)
    assert issubclass(CourseEditingDeniedError, LMSRuleError)
    assert issubclass(MaterialAccessDeniedError, LMSRuleError)
    assert issubclass(MaterialAuthoringDeniedError, LMSRuleError)


def test_material_details_dataclass():
    m = MaterialDetails(
        title="Lecture 1 Slides",
        section_title="Module 1: Introduction",
        material_type=MaterialType.FILE,
        section_type=SectionType.MODULE,
        status=MaterialStatus.PUBLISHED,
    )
    assert m.title == "Lecture 1 Slides"
    assert m.section_title == "Module 1: Introduction"
    assert m.material_type == MaterialType.FILE
    assert m.status == MaterialStatus.PUBLISHED


def test_validate_material_details_valid():
    validate_material_details(
        title="Intro Notes",
        section_title="Week 1",
        material_type=MaterialType.NOTE,
        section_type=SectionType.WEEK,
        status=MaterialStatus.PUBLISHED,
        content="Welcome to the course notes",
    )
    validate_material_details(
        title="Documentation Link",
        section_title="Module 1",
        material_type=MaterialType.LINK,
        section_type=SectionType.MODULE,
        status=MaterialStatus.PUBLISHED,
        link_url="https://docs.python.org",
    )
    validate_material_details(
        title="Scheduled Chapter",
        section_title="Week 2",
        material_type=MaterialType.FILE,
        section_type=SectionType.WEEK,
        status=MaterialStatus.SCHEDULED,
        release_at=datetime(2026, 12, 1, 10, 0, tzinfo=UTC),
    )


def test_validate_material_details_invalid():
    # Empty title
    with pytest.raises(LMSRuleError, match="title cannot be empty"):
        validate_material_details(
            title="",
            section_title="Week 1",
            material_type=MaterialType.NOTE,
            section_type=SectionType.WEEK,
            status=MaterialStatus.PUBLISHED,
            content="Hello",
        )

    # Empty section
    with pytest.raises(LMSRuleError, match="Section title cannot be empty"):
        validate_material_details(
            title="Syllabus",
            section_title="",
            material_type=MaterialType.NOTE,
            section_type=SectionType.WEEK,
            status=MaterialStatus.PUBLISHED,
            content="Hello",
        )

    # Invalid type
    with pytest.raises(LMSRuleError, match="Invalid material type"):
        validate_material_details(
            title="Video",
            section_title="Week 1",
            material_type="video",
            section_type=SectionType.WEEK,
            status=MaterialStatus.PUBLISHED,
        )

    # Scheduled without release_at
    with pytest.raises(LMSRuleError, match="Scheduled material requires a valid release date"):
        validate_material_details(
            title="Midterm prep",
            section_title="Week 5",
            material_type=MaterialType.NOTE,
            section_type=SectionType.WEEK,
            status=MaterialStatus.SCHEDULED,
            release_at=None,
        )

    # Invalid link
    with pytest.raises(LMSRuleError, match="Link URL must start with"):
        validate_material_details(
            title="Bad Link",
            section_title="Week 1",
            material_type=MaterialType.LINK,
            section_type=SectionType.WEEK,
            status=MaterialStatus.PUBLISHED,
            link_url="ftp://files.example.com",
        )

    # Note with empty content
    with pytest.raises(LMSRuleError, match="Note materials require content text"):
        validate_material_details(
            title="Blank Note",
            section_title="Week 1",
            material_type=MaterialType.NOTE,
            section_type=SectionType.WEEK,
            status=MaterialStatus.PUBLISHED,
            content="",
        )


def test_validate_announcement_details_valid():
    validate_announcement_details(
        title="Midterm Exam Schedule",
        content="Exam will be held on Friday at 10:00 in Room 101.",
    )
    details = AnnouncementDetails(
        title="Quiz 2",
        content="Topics: Chapters 3-4.",
    )
    assert details.title == "Quiz 2"


def test_validate_announcement_details_invalid():
    # Empty title
    with pytest.raises(LMSRuleError, match="Announcement title cannot be empty"):
        validate_announcement_details(title="", content="Valid content")

    # Whitespace title
    with pytest.raises(LMSRuleError, match="Announcement title cannot be empty"):
        validate_announcement_details(title="   ", content="Valid content")

    # Title exceeds 200 characters
    with pytest.raises(LMSRuleError, match="Announcement title cannot exceed 200 characters"):
        validate_announcement_details(title="X" * 201, content="Valid content")

    # Empty content
    with pytest.raises(LMSRuleError, match="Announcement content cannot be empty"):
        validate_announcement_details(title="Valid title", content="")

    # Whitespace content
    with pytest.raises(LMSRuleError, match="Announcement content cannot be empty"):
        validate_announcement_details(title="Valid title", content="   ")


def test_assignment_details_dataclass():
    a = AssignmentDetails(
        title="Project Milestone 1",
        instructions="Complete ER design and schema diagrams.",
        submission_type=SubmissionType.FILE,
        points_possible=Decimal("150.00"),
        status=AssignmentStatus.DRAFT,
    )
    assert a.title == "Project Milestone 1"
    assert a.submission_type == "file"
    assert a.points_possible == Decimal("150.00")
    assert a.status == "draft"


def test_validate_assignment_details_valid():
    now = datetime.now(UTC)
    due = now + timedelta(days=7)
    release = now + timedelta(days=1)

    # Valid draft
    validate_assignment_details(
        title="Draft Homework",
        submission_type=SubmissionType.FILE,
        status=AssignmentStatus.DRAFT,
    )

    # Valid published
    validate_assignment_details(
        title="Published Homework",
        instructions="Submit PDF.",
        submission_type=SubmissionType.FILE,
        status=AssignmentStatus.PUBLISHED,
        points_possible=100,
        due_at=due,
    )

    # Valid scheduled
    validate_assignment_details(
        title="Scheduled Homework",
        instructions="Submit link.",
        submission_type=SubmissionType.LINK,
        status=AssignmentStatus.SCHEDULED,
        points_possible=50,
        due_at=due,
        release_at=release,
    )


def test_validate_assignment_details_invalid_title():
    with pytest.raises(LMSRuleError, match="Assignment title cannot be empty"):
        validate_assignment_details(
            title="",
            submission_type=SubmissionType.FILE,
            status=AssignmentStatus.DRAFT,
        )

    with pytest.raises(LMSRuleError, match="exceed 200 characters"):
        validate_assignment_details(
            title="X" * 201,
            submission_type=SubmissionType.FILE,
            status=AssignmentStatus.DRAFT,
        )


def test_validate_assignment_details_invalid_submission_type_and_status():
    with pytest.raises(LMSRuleError, match="Invalid submission type"):
        validate_assignment_details(
            title="Assignment",
            submission_type="video",
            status=AssignmentStatus.DRAFT,
        )

    with pytest.raises(LMSRuleError, match="Invalid assignment status"):
        validate_assignment_details(
            title="Assignment",
            submission_type=SubmissionType.FILE,
            status="archived",
        )


def test_validate_assignment_details_invalid_points():
    with pytest.raises(LMSRuleError, match="greater than zero"):
        validate_assignment_details(
            title="Assignment",
            submission_type=SubmissionType.FILE,
            status=AssignmentStatus.DRAFT,
            points_possible=0,
        )

    with pytest.raises(LMSRuleError, match="greater than zero"):
        validate_assignment_details(
            title="Assignment",
            submission_type=SubmissionType.FILE,
            status=AssignmentStatus.DRAFT,
            points_possible=-10,
        )


def test_validate_assignment_details_publication_requirements():
    now = datetime.now(UTC)
    due = now + timedelta(days=7)

    # Published without instructions fails BR-LMS-009
    with pytest.raises(LMSRuleError, match="Published assignment requires instructions"):
        validate_assignment_details(
            title="Assignment",
            submission_type=SubmissionType.FILE,
            status=AssignmentStatus.PUBLISHED,
            due_at=due,
            points_possible=100,
            instructions="",
        )

    # Published without due_at fails BR-LMS-009
    with pytest.raises(LMSRuleError, match="Published assignment requires a valid due date"):
        validate_assignment_details(
            title="Assignment",
            submission_type=SubmissionType.FILE,
            status=AssignmentStatus.PUBLISHED,
            due_at=None,
            points_possible=100,
            instructions="Submit work.",
        )


def test_validate_assignment_details_scheduled_and_date_order():
    now = datetime.now(UTC)
    due = now + timedelta(days=5)

    # Scheduled without release_at
    with pytest.raises(LMSRuleError, match="Scheduled assignment requires a valid release date"):
        validate_assignment_details(
            title="Assignment",
            submission_type=SubmissionType.TEXT,
            status=AssignmentStatus.SCHEDULED,
            due_at=due,
            points_possible=100,
            instructions="Write essay.",
            release_at=None,
        )

    # Release after due date
    with pytest.raises(LMSRuleError, match="release date cannot be after the due date"):
        validate_assignment_details(
            title="Assignment",
            submission_type=SubmissionType.TEXT,
            status=AssignmentStatus.SCHEDULED,
            due_at=now,
            release_at=now + timedelta(days=1),
            points_possible=100,
            instructions="Write essay.",
        )


def test_assignment_domain_errors():
    assert issubclass(AssignmentAccessDeniedError, LMSRuleError)
    assert issubclass(AssignmentAuthoringDeniedError, LMSRuleError)
