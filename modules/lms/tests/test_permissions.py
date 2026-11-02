from unittest.mock import MagicMock
import pytest
from rest_framework.test import APIRequestFactory
from modules.lms.api.permissions import (
    IsCourseMember,
    IsCourseStaff,
    IsEnrolledStudent,
    IsInstructor,
    IsObserverReadOnly,
    IsTeachingAssistant,
    get_course_id_from_request_or_view,
    get_user_roles,
)
from modules.lms.domain.constants import Role
from modules.lms.models import Course, CourseMembership, Grade, Submission


@pytest.fixture
def course(db):
    return Course.objects.create(
        code="CS801",
        title="Security & Permissions",
        academic_year=2026,
        semester=1,
    )


@pytest.fixture
def factory():
    return APIRequestFactory()


def make_user(user_id: int):
    user = MagicMock()
    user.user_id = user_id
    user.id = user_id
    user.is_authenticated = True
    return user


@pytest.mark.django_db
def test_course_membership_and_role_permissions(course, factory):
    # Setup users
    CourseMembership.objects.create(course=course, user_id=1, role=Role.INSTRUCTOR, is_active=True)
    CourseMembership.objects.create(course=course, user_id=2, role=Role.TA, is_active=True)
    CourseMembership.objects.create(course=course, user_id=3, role=Role.STUDENT, is_active=True)
    CourseMembership.objects.create(course=course, user_id=4, role=Role.OBSERVER, is_active=True)
    CourseMembership.objects.create(course=course, user_id=5, role=Role.STUDENT, is_active=False)

    view = MagicMock()
    view.kwargs = {"course_id": course.id}

    # IsCourseMember
    perm_member = IsCourseMember()
    req_inst = factory.get("/")
    req_inst.user = make_user(1)
    assert perm_member.has_permission(req_inst, view) is True

    req_inactive = factory.get("/")
    req_inactive.user = make_user(5)
    assert perm_member.has_permission(req_inactive, view) is False

    req_anon = factory.get("/")
    req_anon.user = MagicMock(is_authenticated=False)
    assert perm_member.has_permission(req_anon, view) is False

    # IsCourseStaff
    perm_staff = IsCourseStaff()
    assert perm_staff.has_permission(req_inst, view) is True

    req_ta = factory.get("/")
    req_ta.user = make_user(2)
    assert perm_staff.has_permission(req_ta, view) is True

    req_student = factory.get("/")
    req_student.user = make_user(3)
    assert perm_staff.has_permission(req_student, view) is False

    # IsInstructor
    perm_instructor = IsInstructor()
    assert perm_instructor.has_permission(req_inst, view) is True
    assert perm_instructor.has_permission(req_ta, view) is False

    # IsTeachingAssistant
    perm_ta = IsTeachingAssistant()
    assert perm_ta.has_permission(req_ta, view) is True
    assert perm_ta.has_permission(req_student, view) is False

    # IsEnrolledStudent
    perm_student = IsEnrolledStudent()
    assert perm_student.has_permission(req_student, view) is True
    assert perm_student.has_permission(req_inst, view) is False


@pytest.mark.django_db
def test_observer_read_only_and_data_isolation(course, factory):
    perm_observer = IsObserverReadOnly()

    # Safe method GET allowed
    req_get = factory.get("/")
    req_get.user = make_user(4)
    assert perm_observer.has_permission(req_get, MagicMock()) is True

    # Mutating POST denied
    req_post = factory.post("/", {})
    req_post.user = make_user(4)
    assert perm_observer.has_permission(req_post, MagicMock()) is False

    # Observer object access to Submission or Grade strictly denied
    dummy_sub = MagicMock(spec=Submission)
    assert perm_observer.has_object_permission(req_get, MagicMock(), dummy_sub) is False

    dummy_grade = MagicMock(spec=Grade)
    assert perm_observer.has_object_permission(req_get, MagicMock(), dummy_grade) is False


@pytest.mark.django_db
def test_multi_role_cardinality(course, factory):
    # User 99 has BOTH TA and Student active memberships
    CourseMembership.objects.create(course=course, user_id=99, role=Role.TA, is_active=True)
    CourseMembership.objects.create(course=course, user_id=99, role=Role.STUDENT, is_active=True)

    view = MagicMock()
    view.kwargs = {"course_id": course.id}
    req = factory.get("/")
    req.user = make_user(99)

    # Should satisfy IsCourseStaff, IsTeachingAssistant, AND IsEnrolledStudent
    assert IsCourseStaff().has_permission(req, view) is True
    assert IsTeachingAssistant().has_permission(req, view) is True
    assert IsEnrolledStudent().has_permission(req, view) is True
    # But not Instructor
    assert IsInstructor().has_permission(req, view) is False
