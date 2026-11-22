"""Tests for workspace management services (CFR-LMS-002, BR-LMS-003, BR-LMS-004)."""
import pytest

from conftest import make_principal
from core.api.exceptions import BadRequestError, NotFoundError, PermissionDeniedError
from modules.courses.services import workspace as workspace_svc
from modules.courses.tests.factories import add_member, make_workspace


@pytest.mark.django_db
def test_faculty_can_update_workspace():
    ws = make_workspace(
        title="Old Title",
        syllabus="Old Syllabus",
        schedule="Old Schedule",
    )
    fac_p = make_principal(user_id=1, kind="faculty")
    add_member(ws, user_id=1, role="instructor")

    updated = workspace_svc.update_workspace(
        workspace_id=ws.id,
        principal=fac_p,
        title="New Title",
        syllabus="New Syllabus 2026",
        schedule="Tue/Thu 11:00 AM",
        allow_ta_announcements=True,
    )

    ws.refresh_from_db()
    assert ws.title == "New Title"
    assert ws.syllabus == "New Syllabus 2026"
    assert ws.schedule == "Tue/Thu 11:00 AM"
    assert ws.allow_ta_announcements is True
    assert updated.title == "New Title"


@pytest.mark.django_db
def test_update_workspace_validates_non_empty_title():
    ws = make_workspace()
    fac_p = make_principal(user_id=1, kind="faculty")
    add_member(ws, user_id=1, role="instructor")

    with pytest.raises(BadRequestError, match="cannot be empty"):
        workspace_svc.update_workspace(
            workspace_id=ws.id,
            principal=fac_p,
            title="   ",
        )


@pytest.mark.django_db
def test_ta_cannot_update_workspace():
    ws = make_workspace()
    ta_p = make_principal(user_id=2, kind="student")
    add_member(ws, user_id=2, role="ta")

    with pytest.raises(PermissionDeniedError, match="Only assigned faculty instructors"):
        workspace_svc.update_workspace(
            workspace_id=ws.id,
            principal=ta_p,
            title="TA Title Change",
        )


@pytest.mark.django_db
def test_observer_cannot_update_workspace():
    ws = make_workspace()
    obs_p = make_principal(user_id=3, kind="operator")
    add_member(ws, user_id=3, role="observer")

    with pytest.raises(PermissionDeniedError, match="Only assigned faculty instructors"):
        workspace_svc.update_workspace(
            workspace_id=ws.id,
            principal=obs_p,
            syllabus="Observer modification attempt",
        )


@pytest.mark.django_db
def test_student_cannot_update_workspace():
    ws = make_workspace()
    stu_p = make_principal(user_id=4, kind="student")
    add_member(ws, user_id=4, role="student")

    with pytest.raises(PermissionDeniedError, match="Only assigned faculty instructors"):
        workspace_svc.update_workspace(
            workspace_id=ws.id,
            principal=stu_p,
            title="Student Title Change",
        )


@pytest.mark.django_db
def test_non_member_gets_not_found():
    ws = make_workspace()
    foreign_p = make_principal(user_id=99)

    with pytest.raises(NotFoundError):
        workspace_svc.update_workspace(
            workspace_id=ws.id,
            principal=foreign_p,
            title="Foreign Modification",
        )
