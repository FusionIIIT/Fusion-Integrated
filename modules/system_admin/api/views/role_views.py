"""Role management API views."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.system_admin.api.serializers import (
    AssignRoleSerializer,
    ExtendRoleSerializer,
    ReassignRoleSerializer,
    RevokeRoleSerializer,
    RoleAssignmentSerializer,
    RoleDirectoryEntrySerializer,
)
from modules.system_admin.domain.exceptions import (
    DomainValidationError,
    RoleAssignmentNotFoundError,
    SeparationOfDutiesConflictError,
    SingularRoleOccupancyError,
    SystemAdminDomainError,
    UserNotFoundError,
)
from modules.system_admin.selectors.role_selectors import (
    get_role_directory,
    list_role_assignments,
)
from modules.system_admin.services.role_service import (
    assign_role,
    extend_role_validity,
    reassign_role,
    revoke_role,
)

MODULE = HasModuleGrant("system_admin")


def _actor_id(request) -> int:
    principal = getattr(request, "principal", None)
    return getattr(principal, "user_id", 1) or 1


def _ip(request) -> str | None:
    return request.META.get("REMOTE_ADDR")


class RoleListView(APIView):
    permission_classes = [MODULE, HasPermission("system_admin.role.view")]

    @extend_schema(responses={200: RoleAssignmentSerializer(many=True)})
    def get(self, request):
        mode = request.query_params.get("mode")
        if mode == "directory":
            directory = get_role_directory()
            return Response(RoleDirectoryEntrySerializer(directory, many=True).data)

        user_id_param = request.query_params.get("user_id")
        user_id = int(user_id_param) if user_id_param else None
        role_code = request.query_params.get("role_code")
        status_filter = request.query_params.get("status")

        assignments = list_role_assignments(
            user_id=user_id,
            role_code=role_code,
            status=status_filter,
        )
        return Response(RoleAssignmentSerializer(assignments, many=True).data)


class RoleAssignView(APIView):
    permission_classes = [MODULE, HasPermission("system_admin.role.manage")]

    @extend_schema(request=AssignRoleSerializer, responses={201: RoleAssignmentSerializer})
    def post(self, request):
        serializer = AssignRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            assignment = assign_role(
                role_code=data["role_code"],
                user_id=data["user_id"],
                start_date=data["start_date"],
                end_date=data.get("end_date"),
                scope=data.get("scope", ""),
                reason=data.get("reason", ""),
                role_name=data.get("role_name", ""),
                is_singular=data.get("is_singular", False),
                actor_id=_actor_id(request),
                ip_address=_ip(request),
            )
        except (
            SingularRoleOccupancyError,
            SeparationOfDutiesConflictError,
            DomainValidationError,
            SystemAdminDomainError,
        ) as e:
            raise BadRequestError(str(e)) from e
        except (UserNotFoundError, RoleAssignmentNotFoundError) as e:
            raise NotFoundError(str(e)) from e

        return Response(
            RoleAssignmentSerializer(assignment).data,
            status=status.HTTP_201_CREATED,
        )


class RoleReassignView(APIView):
    permission_classes = [MODULE, HasPermission("system_admin.role.manage")]

    @extend_schema(request=ReassignRoleSerializer, responses={200: RoleAssignmentSerializer})
    def post(self, request, role_id: int | None = None, pk: int | None = None):
        rid = role_id if role_id is not None else pk
        serializer = ReassignRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            _, new_assignment = reassign_role(
                role_assignment_id=rid,
                new_user_id=data["new_user_id"],
                effective_date=data["effective_date"],
                reason=data["reason"],
                transfer_pending_tasks=data.get("transfer_pending_tasks", True),
                actor_id=_actor_id(request),
                ip_address=_ip(request),
            )
        except SingularRoleOccupancyError as e:
            raise ConflictError(str(e)) from e
        except (RoleAssignmentNotFoundError, UserNotFoundError) as e:
            raise NotFoundError(str(e)) from e
        except (DomainValidationError, SystemAdminDomainError) as e:
            raise BadRequestError(str(e)) from e

        return Response(RoleAssignmentSerializer(new_assignment).data)


class RoleRevokeView(APIView):
    permission_classes = [MODULE, HasPermission("system_admin.role.manage")]

    @extend_schema(request=RevokeRoleSerializer, responses={200: RoleAssignmentSerializer})
    def post(self, request, role_id: int | None = None, pk: int | None = None):
        rid = role_id if role_id is not None else pk
        serializer = RevokeRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            assignment = revoke_role(
                role_assignment_id=rid,
                reason=data["reason"],
                is_emergency=data.get("is_emergency", False),
                actor_id=_actor_id(request),
                ip_address=_ip(request),
            )
        except RoleAssignmentNotFoundError as e:
            raise NotFoundError(str(e)) from e
        except (DomainValidationError, SystemAdminDomainError) as e:
            raise BadRequestError(str(e)) from e

        return Response(RoleAssignmentSerializer(assignment).data)


class RoleExtendView(APIView):
    permission_classes = [MODULE, HasPermission("system_admin.role.manage")]

    @extend_schema(request=ExtendRoleSerializer, responses={200: RoleAssignmentSerializer})
    def post(self, request, role_id: int | None = None, pk: int | None = None):
        rid = role_id if role_id is not None else pk
        serializer = ExtendRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            assignment = extend_role_validity(
                role_assignment_id=rid,
                new_end_date=data["new_end_date"],
                reason=data["reason"],
                actor_id=_actor_id(request),
                ip_address=_ip(request),
            )
        except RoleAssignmentNotFoundError as e:
            raise NotFoundError(str(e)) from e
        except (DomainValidationError, SystemAdminDomainError) as e:
            raise BadRequestError(str(e)) from e

        return Response(RoleAssignmentSerializer(assignment).data)
