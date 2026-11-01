"""Unit tests for LMS pure domain rules and entities."""
import pytest

from modules.lms.domain.entities import (
    CourseDetails,
    CourseRole,
    CourseStatus,
    validate_course_details,
)
from modules.lms.domain.errors import (
    CourseAccessDeniedError,
    CourseEditingDeniedError,
    LMSRuleError,
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
