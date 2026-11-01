"""Tests for course access scoping and visibility isolation (BR-LMS-001, AFR-LMS-001.3)."""
import pytest

from conftest import make_principal
from modules.courses.selectors import scoping
from modules.courses.tests.factories import add_member, make_workspace


@pytest.mark.django_db
def test_student_only_sees_enrolled_courses():
    ws1 = make_workspace(code="CS201", semester="Monsoon 2026")
    ws2 = make_workspace(code="CS202", semester="Monsoon 2026")
    ws_other = make_workspace(code="EE101", semester="Monsoon 2026")

    student_p = make_principal(user_id=10, kind="student")
    add_member(ws1, user_id=10, role="student")
    add_member(ws2, user_id=10, role="student")

    # Another student enrolled in EE101
    add_member(ws_other, user_id=99, role="student")

    visible = scoping.visible_workspaces(student_p)
    visible_codes = set(visible.values_list("code", flat=True))

    assert visible_codes == {"CS201", "CS202"}
    assert "EE101" not in visible_codes


@pytest.mark.django_db
def test_faculty_only_sees_assigned_courses():
    ws_assigned = make_workspace(code="CS301", semester="Monsoon 2026")
    make_workspace(code="CS302", semester="Monsoon 2026")

    fac_p = make_principal(user_id=20, kind="faculty")
    add_member(ws_assigned, user_id=20, role="instructor")

    visible = scoping.visible_workspaces(fac_p)
    assert list(visible) == [ws_assigned]


@pytest.mark.django_db
def test_ta_and_observer_see_linked_courses():
    ws = make_workspace(code="CS401", semester="Monsoon 2026")

    ta_p = make_principal(user_id=30, kind="student")
    obs_p = make_principal(user_id=40, kind="operator")

    add_member(ws, user_id=30, role="ta")
    add_member(ws, user_id=40, role="observer")

    assert list(scoping.visible_workspaces(ta_p)) == [ws]
    assert list(scoping.visible_workspaces(obs_p)) == [ws]


@pytest.mark.django_db
def test_is_course_instructor_check():
    ws = make_workspace()
    fac_p = make_principal(user_id=1)
    ta_p = make_principal(user_id=2)
    stu_p = make_principal(user_id=3)
    obs_p = make_principal(user_id=4)

    add_member(ws, 1, "instructor")
    add_member(ws, 2, "ta")
    add_member(ws, 3, "student")
    add_member(ws, 4, "observer")

    assert scoping.is_course_instructor(ws, fac_p) is True
    assert scoping.is_course_instructor(ws, ta_p) is False
    assert scoping.is_course_instructor(ws, stu_p) is False
    assert scoping.is_course_instructor(ws, obs_p) is False


@pytest.mark.django_db
def test_get_workspace_personnel_ids():
    ws = make_workspace()
    add_member(ws, 101, "instructor")
    add_member(ws, 102, "instructor")
    add_member(ws, 201, "ta")
    add_member(ws, 301, "student")

    inst_ids, ta_ids = scoping.get_workspace_personnel_ids(ws)
    assert sorted(inst_ids) == [101, 102]
    assert ta_ids == [201]
