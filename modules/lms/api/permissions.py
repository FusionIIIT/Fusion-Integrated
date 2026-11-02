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


def get_resolved_role(request, course_id: int | None) -> str | None:
    """
    Resolves the safe, explicit authorization role for a user in a course.
    - If user has 0 active memberships: returns None.
    - If user has exactly 1 active membership: returns that role unambiguously.
    - If user has multiple active memberships:
        Requires explicit role context (header X-LMS-Role, query ?as_role=, or IAM active_role).
        If explicit role is one of user's active roles in that course, returns it.
        Otherwise returns None (denies ambiguous multi-role context pending disambiguation).
    """
    user_id = get_request_user_id(request)
    if user_id is None or course_id is None:
        return None

    active_roles = set(
        CourseMembership.objects.filter(
            course_id=course_id,
            user_id=user_id,
            is_active=True,
        ).values_list("role", flat=True)
    )
    if not active_roles:
        return None

    if len(active_roles) == 1:
        return next(iter(active_roles))

    explicit_role = (
        request.headers.get("X-LMS-Role")
        or getattr(request, "query_params", {}).get("as_role")
        or getattr(request.user, "active_role", None)
    )

    if explicit_role and explicit_role in active_roles:
        return explicit_role

    return None


class IsCourseMember(BasePermission):
    """Allows access to users who have an active, resolved role in the course."""

    def has_permission(self, request, view):
        course_id = get_course_id_from_request_or_view(request, view)
        if not course_id:
            return True
        return get_resolved_role(request, course_id) is not None

    def has_object_permission(self, request, view, obj):
        course_id = get_course_id_from_request_or_view(request, view, obj)
        return get_resolved_role(request, course_id) is not None


class IsCourseStaff(BasePermission):
    """Allows access to users acting as instructors or teaching assistants."""

    def has_permission(self, request, view):
        course_id = get_course_id_from_request_or_view(request, view)
        if not course_id:
            return True
        role = get_resolved_role(request, course_id)
        return role in (Role.INSTRUCTOR, Role.TA)

    def has_object_permission(self, request, view, obj):
        course_id = get_course_id_from_request_or_view(request, view, obj)
        role = get_resolved_role(request, course_id)
        return role in (Role.INSTRUCTOR, Role.TA)


class IsInstructor(BasePermission):
    """Allows access only to users acting as instructors."""

    def has_permission(self, request, view):
        course_id = get_course_id_from_request_or_view(request, view)
        if not course_id:
            return True
        return get_resolved_role(request, course_id) == Role.INSTRUCTOR

    def has_object_permission(self, request, view, obj):
        course_id = get_course_id_from_request_or_view(request, view, obj)
        return get_resolved_role(request, course_id) == Role.INSTRUCTOR


class IsTeachingAssistant(BasePermission):
    """Allows access only to users acting as teaching assistants."""

    def has_permission(self, request, view):
        course_id = get_course_id_from_request_or_view(request, view)
        if not course_id:
            return True
        return get_resolved_role(request, course_id) == Role.TA

    def has_object_permission(self, request, view, obj):
        course_id = get_course_id_from_request_or_view(request, view, obj)
        return get_resolved_role(request, course_id) == Role.TA


class IsEnrolledStudent(BasePermission):
    """Allows access only to users acting as enrolled students."""

    def has_permission(self, request, view):
        course_id = get_course_id_from_request_or_view(request, view)
        if not course_id:
            return True
        return get_resolved_role(request, course_id) == Role.STUDENT

    def has_object_permission(self, request, view, obj):
        course_id = get_course_id_from_request_or_view(request, view, obj)
        return get_resolved_role(request, course_id) == Role.STUDENT


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
