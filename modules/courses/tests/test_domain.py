"""Domain layer tests (pure Python)."""
import pytest

from modules.courses.domain.entities import (
    WorkspaceUpdateDTO,
    validate_faculty_editor,
    validate_membership_role,
)
from modules.courses.domain.errors import (
    InvalidCourseDataError,
    UnauthorizedCourseActionError,
)


def test_workspace_update_dto_valid():
    dto = WorkspaceUpdateDTO(title="Advanced Algorithms", syllabus="Unit 1, Unit 2")
    dto.validate()


def test_workspace_update_dto_empty_title_raises():
    dto = WorkspaceUpdateDTO(title="   ")
    with pytest.raises(InvalidCourseDataError, match="cannot be empty"):
        dto.validate()


def test_validate_faculty_editor_success():
    validate_faculty_editor("instructor")


@pytest.mark.parametrize("role", ["ta", "student", "observer", None, "unknown"])
def test_validate_faculty_editor_rejects_non_instructor(role):
    with pytest.raises(UnauthorizedCourseActionError, match="Only assigned faculty"):
        validate_faculty_editor(role)


def test_validate_membership_role():
    validate_membership_role("instructor")
    validate_membership_role("ta")
    validate_membership_role("student")
    validate_membership_role("observer")

    with pytest.raises(InvalidCourseDataError, match="Unknown membership role"):
        validate_membership_role("superadmin")
