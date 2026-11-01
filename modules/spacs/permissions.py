"""SPACS role permissions, evaluated against the authenticated IAM principal."""
from rest_framework.permissions import SAFE_METHODS, BasePermission

STUDENT_ROLE = "student"
ASSISTANT_ROLE = "spacs_assistant"
CONVENER_ROLE = "spacs_convener"

P_APPLICATION_CREATE = "spacs.application.create"
P_APPLICATION_VIEW_SELF = "spacs.application.view_self"
P_APPLICATION_UPDATE = "spacs.application.update"
P_APPLICATION_WITHDRAW = "spacs.application.delete"
P_APPLICATION_VIEW = "spacs.application.view"
P_APPLICATION_REVIEW = "spacs.application.review"
P_APPLICATION_APPROVE = "spacs.application.approve"

STUDENT_EDITABLE_STATUSES = {"draft", "correction_required"}
STUDENT_STATUS_CHANGES = {"submitted", "withdrawn"}
STUDENT_CREATE_FIELDS = {"scheme_id", "student_id", "status", "documents_list"}
STUDENT_UPDATE_FIELDS = {"scheme_id", "status", "documents_list"}
DECISION_SOURCE_STATUSES = {"submitted", "under_verification"}
CONVENER_DECISION_STATUSES = {"approved", "rejected", "correction_required"}
ASSISTANT_UPDATE_FIELDS = {"verification_status", "verification_findings"}
CONVENER_UPDATE_FIELDS = {"status", "decision_note"}


def _principal(request):
    return getattr(request, "principal", None)


def _has_role_permission(principal, role, *permissions):
    has_permission = getattr(principal, "has_permission", None)
    return (
        principal is not None
        and getattr(principal, "active_role", None) == role
        and callable(has_permission)
        and any(has_permission(code) for code in permissions)
    )


def _payload(request):
    data = getattr(request, "data", None)
    return data if hasattr(data, "keys") else {}


def _is_owner(application, principal):
    return getattr(application, "student_id", None) == getattr(principal, "user_id", None)


def _is_assigned(application, principal):
    return (
        getattr(application, "assigned_assistant_user_id", None)
        == getattr(principal, "user_id", None)
    )


class IsStudentApplicant(BasePermission):
    """Students may create applications and edit or withdraw their own drafts."""

    message = "You may only access or change your own eligible applications."

    def has_permission(self, request, view):
        principal = _principal(request)
        method = request.method
        action = getattr(view, "action", None)

        if action == "submit":
            return _has_role_permission(
                principal, STUDENT_ROLE, P_APPLICATION_UPDATE,
            )
        if method in SAFE_METHODS:
            return _has_role_permission(
                principal, STUDENT_ROLE, P_APPLICATION_VIEW_SELF,
            )
        if method == "POST":
            if not _has_role_permission(principal, STUDENT_ROLE, P_APPLICATION_CREATE):
                return False
            data = _payload(request)
            supplied_student_id = data.get("student_id")
            return (
                set(data) <= STUDENT_CREATE_FIELDS
                and data.get("status", "draft") == "draft"
                and supplied_student_id in (
                    None, "", getattr(principal, "user_id", None),
                    str(getattr(principal, "user_id", "")),
                )
            )
        if method in {"PATCH", "PUT"}:
            return _has_role_permission(principal, STUDENT_ROLE, P_APPLICATION_UPDATE)
        if method == "DELETE":
            return _has_role_permission(principal, STUDENT_ROLE, P_APPLICATION_WITHDRAW)
        return False

    def has_object_permission(self, request, view, obj):
        principal = _principal(request)
        if not _is_owner(obj, principal):
            return False
        if getattr(view, "action", None) == "submit":
            return (
                getattr(obj, "status", None) == "draft"
                and _has_role_permission(
                    principal, STUDENT_ROLE, P_APPLICATION_UPDATE,
                )
            )
        if request.method in SAFE_METHODS:
            return _has_role_permission(
                principal, STUDENT_ROLE, P_APPLICATION_VIEW_SELF,
            )
        if getattr(obj, "status", None) not in STUDENT_EDITABLE_STATUSES:
            return False
        if request.method == "DELETE":
            return _has_role_permission(principal, STUDENT_ROLE, P_APPLICATION_WITHDRAW)
        if request.method in {"PATCH", "PUT"}:
            if not _has_role_permission(principal, STUDENT_ROLE, P_APPLICATION_UPDATE):
                return False
            data = _payload(request)
            new_status = data.get("status")
            return (
                bool(data)
                and set(data) <= STUDENT_UPDATE_FIELDS
                and new_status in (
                    None, "", getattr(obj, "status", None), *STUDENT_STATUS_CHANGES,
                )
            )
        return False

    def scope_queryset(self, request, queryset):
        """Limit applicant list endpoints to the authenticated student's rows."""
        principal = _principal(request)
        if principal is None:
            return queryset.none()
        return queryset.filter(student_id=principal.user_id)


class IsSpacsAssistant(BasePermission):
    """Assistant access is limited to assigned rows and verification fields."""

    message = "You may only verify applications assigned to you."

    def has_permission(self, request, view):
        principal = _principal(request)
        if getattr(view, "action", None) == "verify":
            return _has_role_permission(
                principal, ASSISTANT_ROLE, P_APPLICATION_REVIEW,
            )
        if request.method in SAFE_METHODS:
            return _has_role_permission(principal, ASSISTANT_ROLE, P_APPLICATION_REVIEW)
        if request.method == "PATCH":
            keys = set(_payload(request))
            return bool(keys) and keys <= ASSISTANT_UPDATE_FIELDS and (
                _has_role_permission(principal, ASSISTANT_ROLE, P_APPLICATION_REVIEW)
            )
        return False

    def has_object_permission(self, request, view, obj):
        principal = _principal(request)
        if getattr(view, "action", None) == "verify":
            return (
                _is_assigned(obj, principal)
                and _has_role_permission(
                    principal, ASSISTANT_ROLE, P_APPLICATION_REVIEW,
                )
            )
        return (
            _is_assigned(obj, principal)
            and _has_role_permission(principal, ASSISTANT_ROLE, P_APPLICATION_REVIEW)
            and (
                request.method in SAFE_METHODS
                or (
                    request.method == "PATCH"
                    and bool(set(_payload(request)))
                    and set(_payload(request)) <= ASSISTANT_UPDATE_FIELDS
                )
            )
        )

    def scope_queryset(self, request, queryset):
        """Filter list endpoints; DRF does not run object permissions per result."""
        principal = _principal(request)
        if principal is None:
            return queryset.none()
        return queryset.filter(assigned_assistant_user_id=principal.user_id)


class IsSpacsConvener(BasePermission):
    """Conveners may make final decisions, but cannot create or edit other fields."""

    message = "You do not have authority to make this application decision."

    def has_permission(self, request, view):
        principal = _principal(request)
        if getattr(view, "action", None) in {
            "approve", "reject", "return_for_correction",
        }:
            return _has_role_permission(
                principal, CONVENER_ROLE, P_APPLICATION_APPROVE,
            )
        if request.method in SAFE_METHODS:
            return _has_role_permission(principal, CONVENER_ROLE, P_APPLICATION_VIEW)
        if request.method == "PATCH":
            data = _payload(request)
            return (
                set(data) <= CONVENER_UPDATE_FIELDS
                and data.get("status") in CONVENER_DECISION_STATUSES
                and _has_role_permission(
                    principal, CONVENER_ROLE, P_APPLICATION_APPROVE,
                )
            )
        return False

    def has_object_permission(self, request, view, obj):
        principal = _principal(request)
        action_statuses = {
            "approve": "approved",
            "reject": "rejected",
            "return_for_correction": "correction_required",
        }
        action = getattr(view, "action", None)
        if action in action_statuses:
            return (
                getattr(obj, "status", None) in DECISION_SOURCE_STATUSES
                and _has_role_permission(
                    principal, CONVENER_ROLE, P_APPLICATION_APPROVE,
                )
            )
        if request.method in SAFE_METHODS:
            return _has_role_permission(principal, CONVENER_ROLE, P_APPLICATION_VIEW)
        data = _payload(request)
        return (
            request.method == "PATCH"
            and getattr(obj, "status", None) in DECISION_SOURCE_STATUSES
            and set(data) <= CONVENER_UPDATE_FIELDS
            and data.get("status") in CONVENER_DECISION_STATUSES
            and _has_role_permission(principal, CONVENER_ROLE, P_APPLICATION_APPROVE)
        )


class IsStudentSupportingDocument(BasePermission):
    """Students may manage their own supporting documents only."""

    message = "You may only access or change your own supporting documents."

    def has_permission(self, request, view):
        principal = _principal(request)
        if request.method in SAFE_METHODS:
            return _has_role_permission(
                principal, STUDENT_ROLE, P_APPLICATION_VIEW_SELF,
            )
        if request.method == "POST":
            return (
                set(_payload(request)) <= {"document_type", "file_url", "is_reusable"}
                and _has_role_permission(
                    principal, STUDENT_ROLE, P_APPLICATION_CREATE,
                )
            )
        if request.method in {"PATCH", "PUT"}:
            return (
                set(_payload(request)) <= {"document_type", "file_url", "is_reusable"}
                and _has_role_permission(
                    principal, STUDENT_ROLE, P_APPLICATION_UPDATE,
                )
            )
        if request.method == "DELETE":
            return _has_role_permission(
                principal, STUDENT_ROLE, P_APPLICATION_WITHDRAW,
            )
        return False

    def has_object_permission(self, request, view, obj):
        principal = _principal(request)
        if getattr(obj, "owner_user_id", None) != getattr(principal, "user_id", None):
            return False
        if request.method in SAFE_METHODS:
            return _has_role_permission(
                principal, STUDENT_ROLE, P_APPLICATION_VIEW_SELF,
            )
        if request.method == "POST":
            return _has_role_permission(
                principal, STUDENT_ROLE, P_APPLICATION_CREATE,
            )
        if request.method in {"PATCH", "PUT"}:
            return _has_role_permission(
                principal, STUDENT_ROLE, P_APPLICATION_UPDATE,
            )
        if request.method == "DELETE":
            return _has_role_permission(
                principal, STUDENT_ROLE, P_APPLICATION_WITHDRAW,
            )
        return False

    def scope_queryset(self, request, queryset):
        principal = _principal(request)
        if principal is None:
            return queryset.none()
        return queryset.filter(owner_user_id=principal.user_id)
