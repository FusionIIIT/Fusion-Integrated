"""Unit tests for LMS pure domain rules and entities."""
from datetime import UTC, datetime

import pytest

from modules.lms.domain.entities import (
    CourseDetails,
    CourseRole,
    CourseStatus,
    MaterialDetails,
    MaterialStatus,
    MaterialType,
    SectionType,
    validate_course_details,
    validate_material_details,
)
from modules.lms.domain.errors import (
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

