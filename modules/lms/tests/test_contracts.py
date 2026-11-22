"""Tests for LMS public cross-module contracts (modules/lms/contracts.py)."""

import pytest

from modules.lms import contracts
from modules.lms.domain.entities import CourseRole
from modules.lms.services import courses as service

pytestmark = pytest.mark.django_db


def test_contracts_plural_queries():
    c1 = service.create_course_workspace(
        course_code="CS201",
        title="Algorithms",
        instructor_user_id=10,
    )
    c2 = service.create_course_workspace(
        course_code="CS202",
        title="Operating Systems",
        instructor_user_id=11,
    )

    service.enroll_member(course_id=c1.id, user_id=100, role=CourseRole.STUDENT.value)
    service.enroll_member(course_id=c2.id, user_id=100, role=CourseRole.STUDENT.value)
    service.enroll_member(course_id=c1.id, user_id=101, role=CourseRole.STUDENT.value)

    # get_courses
    courses_map = contracts.get_courses([c1.id, c2.id, 999])
    assert len(courses_map) == 2
    assert courses_map[c1.id].course_code == "CS201"
    assert courses_map[c2.id].course_code == "CS202"

    # get_student_enrollments
    enrollments = contracts.get_student_enrollments([100, 101, 999])
    assert len(enrollments[100]) == 2
    assert len(enrollments[101]) == 1
    assert len(enrollments[999]) == 0

    # get_instructor_courses
    inst_courses = contracts.get_instructor_courses([10, 11, 999])
    assert len(inst_courses[10]) == 1
    assert len(inst_courses[11]) == 1
    assert len(inst_courses[999]) == 0

    # is_user_in_course
    assert contracts.is_user_in_course(c1.id, 100) is True
    assert contracts.is_user_in_course(c1.id, 999) is False
