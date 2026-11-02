from rest_framework.permissions import SAFE_METHODS, BasePermission
from modules.lms.domain.constants import Role
from modules.lms.models import Course, CourseMembership


def get_request_user_id(request) -> int | None:
    if not (request.user and request.user.is_authenticated):
        return None
    uid = getattr(request.user, "user_id", None)
    if isinstance(uid, int):
        return uid
    uid = getattr(request.user, "id", None)
    if isinstance(uid, int):
        return uid
    if uid is not None and str(uid).isdigit():
        return int(uid)
    return None


def get_course_id_from_request_or_view(request, view, obj=None) -> int | None:
    course_id = view.kwargs.get("course_id") or view.kwargs.get("course_pk")
    if not course_id and hasattr(view, "kwargs") and "pk" in view.kwargs:
        # Check if view is for Course itself
        if getattr(view, "basename", "") == "course":
            course_id = view.kwargs["pk"]

    if obj is not None:
        if isinstance(obj, Course):
            return obj.id
        if hasattr(obj, "course_id"):
            return obj.course_id
        if hasattr(obj, "section") and hasattr(obj.section, "course_id"):
            return obj.section.course_id
        if hasattr(obj, "assignment") and hasattr(obj.assignment, "course_id"):
            return obj.assignment.course_id
        if hasattr(obj, "submission") and hasattr(obj.submission, "assignment"):
            return obj.submission.assignment.course_id
        if hasattr(obj, "grade") and hasattr(obj.grade, "submission"):
            return obj.grade.submission.assignment.course_id

    return int(course_id) if (course_id is not None and str(course_id).isdigit()) else None


def get_user_roles(user_id: int | None, course_id: int | None) -> set[str]:
    if not user_id or not course_id:
        return set()
    return set(
        CourseMembership.objects.filter(
            course_id=course_id,
            user_id=user_id,
            is_active=True,
        ).values_list("role", flat=True)
    )


class IsCourseMember(BasePermission):
    """Allows access to users who have an active membership in the course."""

    def has_permission(self, request, view):
        user_id = get_request_user_id(request)
        if not user_id:
            return False
        course_id = get_course_id_from_request_or_view(request, view)
        if not course_id:
            return True
        return bool(get_user_roles(user_id, course_id))

    def has_object_permission(self, request, view, obj):
        user_id = get_request_user_id(request)
        course_id = get_course_id_from_request_or_view(request, view, obj)
        return bool(get_user_roles(user_id, course_id))


class IsCourseStaff(BasePermission):
    """Allows access to instructors and teaching assistants."""

    def has_permission(self, request, view):
        user_id = get_request_user_id(request)
        if not user_id:
            return False
        course_id = get_course_id_from_request_or_view(request, view)
        if not course_id:
            return True
        roles = get_user_roles(user_id, course_id)
        return bool(roles & {Role.INSTRUCTOR, Role.TA})

    def has_object_permission(self, request, view, obj):
        user_id = get_request_user_id(request)
        course_id = get_course_id_from_request_or_view(request, view, obj)
        roles = get_user_roles(user_id, course_id)
        return bool(roles & {Role.INSTRUCTOR, Role.TA})


class IsInstructor(BasePermission):
    """Allows access only to instructors."""

    def has_permission(self, request, view):
        user_id = get_request_user_id(request)
        if not user_id:
            return False
        course_id = get_course_id_from_request_or_view(request, view)
        if not course_id:
            return True
        return Role.INSTRUCTOR in get_user_roles(user_id, course_id)

    def has_object_permission(self, request, view, obj):
        user_id = get_request_user_id(request)
        course_id = get_course_id_from_request_or_view(request, view, obj)
        return Role.INSTRUCTOR in get_user_roles(user_id, course_id)


class IsTeachingAssistant(BasePermission):
    """Allows access only to teaching assistants."""

    def has_permission(self, request, view):
        user_id = get_request_user_id(request)
        if not user_id:
            return False
        course_id = get_course_id_from_request_or_view(request, view)
        if not course_id:
            return True
        return Role.TA in get_user_roles(user_id, course_id)

    def has_object_permission(self, request, view, obj):
        user_id = get_request_user_id(request)
        course_id = get_course_id_from_request_or_view(request, view, obj)
        return Role.TA in get_user_roles(user_id, course_id)


class IsEnrolledStudent(BasePermission):
    """Allows access to enrolled students."""

    def has_permission(self, request, view):
        user_id = get_request_user_id(request)
        if not user_id:
            return False
        course_id = get_course_id_from_request_or_view(request, view)
        if not course_id:
            return True
        return Role.STUDENT in get_user_roles(user_id, course_id)

    def has_object_permission(self, request, view, obj):
        user_id = get_request_user_id(request)
        course_id = get_course_id_from_request_or_view(request, view, obj)
        return Role.STUDENT in get_user_roles(user_id, course_id)


class IsObserverReadOnly(BasePermission):
    """
    Observers have safe-method read access only to course info/content.
    Observers are strictly denied access to student submissions and grades.
    """

    def has_permission(self, request, view):
        if request.method not in SAFE_METHODS:
            return False
        return True

    def has_object_permission(self, request, view, obj):
        if request.method not in SAFE_METHODS:
            return False
        from modules.lms.models import Grade, GradeAuditLog, Submission

        if isinstance(obj, (Submission, Grade, GradeAuditLog)):
            return False
        return True
