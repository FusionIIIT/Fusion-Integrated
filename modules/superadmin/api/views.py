"""Super Admin API: authenticated, permission-gated proxies to IAM."""
from __future__ import annotations

from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, PermissionDeniedError
from fusion_auth.client import IamUnavailable
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.superadmin.services.iam_admin import IamAdmin, IamAdminError

MODULE = HasModuleGrant("superadmin")
IAM = IamAdmin()
USER_FILTERS = {"gender", "programme", "batch", "discipline", "category", "designation"}


class IamUnavailableError(APIException):
    status_code = 503
    default_detail = "The identity service is unavailable. Try again later."
    default_code = "iam_unavailable"


def _call(fn, *args, **kwargs):
    try:
        return Response(fn(*args, **kwargs))
    except ValueError as exc:
        raise BadRequestError(str(exc)) from exc
    except IamUnavailable as exc:
        raise IamUnavailableError() from exc
    except IamAdminError as exc:
        return Response(exc.payload, status=exc.status_code)


class UserDirectoryView(APIView):
    permission_classes = [MODULE, HasPermission("superadmin.user.view")]

    def get(self, request):
        user_type = request.query_params.get("type", "")
        unknown = set(request.query_params) - USER_FILTERS - {"type"}
        if unknown:
            raise BadRequestError(f"Unsupported filters: {', '.join(sorted(unknown))}.")
        filters = {key: request.query_params[key]
                   for key in USER_FILTERS if request.query_params.get(key)}
        return _call(IAM.list_users, request.auth, user_type, filters)


class CreateUserView(APIView):
    permission_classes = [MODULE, HasPermission("superadmin.user.create")]

    def post(self, request):
        user_type = request.data.get("type")
        payload = request.data.get("user")
        if not isinstance(payload, dict):
            raise BadRequestError("A user object is required.")
        if user_type not in {"faculty", "staff"}:
            raise BadRequestError(
                "The connected IAM documents individual creation for faculty and staff only."
            )
        required = {"username", "first_name", "last_name", "sex", "designation"}
        missing = sorted(key for key in required if not payload.get(key))
        if missing:
            raise BadRequestError("Required fields are missing.", details=[
                {"field": key, "message": "This field is required."} for key in missing
            ])
        return _call(IAM.create_user, request.auth, user_type, payload)


class RoleDirectoryView(APIView):
    permission_classes = [MODULE, HasPermission("superadmin.role.view")]

    def get(self, request):
        return _call(IAM.list_roles, request.auth)


class UserRoleView(APIView):
    permission_classes = [MODULE, HasPermission("superadmin.role.view")]

    def get(self, request, username):
        return _call(IAM.user_roles, request.auth, username)


def _role_names(roles) -> set[str]:
    names = set()
    for role in roles or []:
        name = role.get("name") if isinstance(role, dict) else role
        if isinstance(name, str):
            names.add(name.strip().casefold())
    return names


class UserRoleAssignmentView(APIView):
    permission_classes = [MODULE, HasPermission("superadmin.role.assign")]

    def put(self, request, username):
        roles = request.data.get("roles")
        if not isinstance(roles, list):
            raise BadRequestError("A roles list is required.")
        if any(not isinstance(role, (str, dict)) for role in roles):
            raise BadRequestError("Each role must be a role name or role object.")
        principal = getattr(request, "principal", None)
        current_username = getattr(principal, "username", "")
        if username.casefold() == current_username.casefold():
            def replace_own_roles():
                existing = IAM.user_roles(request.auth, username)
                existing_names = _role_names(
                    existing.get("roles", []) if isinstance(existing, dict) else []
                )
                submitted_names = _role_names(roles)
                if "super admin" in existing_names or "super admin" in submitted_names:
                    raise PermissionDeniedError(
                        "A Super Admin cannot change their own Super Admin status."
                    )
                return IAM.replace_user_roles(request.auth, username, roles)

            return _call(replace_own_roles)
        return _call(IAM.replace_user_roles, request.auth, username, roles)


class PasswordResetView(APIView):
    permission_classes = [MODULE, HasPermission("superadmin.user.update")]

    def post(self, request, username):
        # IAM emails the generated credential; it never returns the password.
        return _call(IAM.reset_password, request.auth, username)


class UserImportView(APIView):
    permission_classes = [MODULE, HasPermission("superadmin.user.bulk_create")]

    def post(self, request):
        csv_file = request.FILES.get("file")
        if not csv_file or not csv_file.name.lower().endswith(".csv"):
            raise BadRequestError("Upload a CSV file in the file field.")
        if csv_file.size > 5 * 1024 * 1024:
            raise BadRequestError("CSV upload exceeds the 5 MB limit.")
        return _call(IAM.bulk_import, request.auth, csv_file)
