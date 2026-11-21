"""REST API Views for modules.system_admin.

Orchestrates selectors and application services behind strict authorization gates.
Traceability: CFR-SA-001..023, UCs (All), BR-SA-001..035, CW-SA-01..03.
"""
from __future__ import annotations

import logging
from typing import Any

from django.http import Http404, HttpResponse
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api import csv as csv_utils
from modules.system_admin.api import serializers as s
from modules.system_admin.api.permissions import (
    DenySelfModification,
    EnforceDataIsolationBoundary,
    IsITHeadPrincipal,
    IsSuperAdminPrincipal,
    RequiresCriticalActionConfirmation,
)
from modules.system_admin.domain import dataclasses as domain_dc
from modules.system_admin.domain import exceptions as domain_exc
from modules.system_admin.models import (
    BasicUser,
    HistoricalDataArchive,
    RoleAssignment,
    RoleDefinition,
    SuperAdminAuditLog,
)
from modules.system_admin import selectors
from modules.system_admin.services import (
    archival as archival_service,
    configuration as config_service,
    purge as purge_service,
    role_management as role_service,
    user_lifecycle as user_service,
)

logger = logging.getLogger(__name__)


def _get_actor_id(request: Any) -> int:
    principal = getattr(request, "principal", None) or getattr(request, "user", None)
    if principal is not None:
        user_id = getattr(principal, "user_id", getattr(principal, "id", None))
        if user_id is not None:
            try:
                return int(user_id)
            except (ValueError, TypeError):
                pass
    return 1  # Default fallback if system/unauthenticated internal request


# ==============================================================================
# 1. USER MANAGEMENT VIEWSET (UC-SA-001..005)
# ==============================================================================


class UserViewSet(viewsets.ViewSet):
    """CRUD, bulk operations, and lifecycle transitions for basic users."""

    permission_classes = [
        IsSuperAdminPrincipal,
        DenySelfModification,
        EnforceDataIsolationBoundary,
    ]

    @extend_schema(request=s.BasicUserCreateSerializer, responses=s.BasicUserDetailSerializer)
    def create(self, request: Any) -> Response:
        serializer = s.BasicUserCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        spec = domain_dc.UserCreationSpec(
            user_kind=data["user_kind"],
            name=data["name"],
            institute_email=data["institute_email"],
            institute_id=data["institute_id"],
            contact_number=data.get("contact_number", ""),
            department=data.get("department", ""),
            programme=data.get("programme", ""),
            discipline=data.get("discipline", ""),
            batch_year=data.get("batch_year"),
            employee_id=data.get("employee_id", ""),
            date_of_joining=data.get("date_of_joining"),
            expected_completion_date=data.get("expected_completion_date"),
        )

        try:
            user = user_service.create_basic_user(
                spec=spec, performed_by_id=_get_actor_id(request)
            )
        except domain_exc.DomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": exc.message}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            s.BasicUserDetailSerializer(user).data, status=status.HTTP_201_CREATED
        )

    @extend_schema(responses=s.BasicUserDetailSerializer)
    def retrieve(self, request: Any, pk: str | None = None) -> Response:
        try:
            user_id = int(pk or 0)
        except (ValueError, TypeError):
            raise NotFound("Invalid user identifier.")

        user = selectors.users.get_user_by_id(user_id)
        if not user:
            raise NotFound("User not found.")

        self.check_object_permissions(request, user)
        return Response(s.BasicUserDetailSerializer(user).data)

    @extend_schema(responses=s.BasicUserDetailSerializer(many=True))
    def list(self, request: Any) -> Response:
        users = selectors.users.list_users(
            user_kind=request.query_params.get("user_kind"),
            status=request.query_params.get("status"),
            department=request.query_params.get("department"),
            programme=request.query_params.get("programme"),
            batch_year=(
                int(request.query_params["batch_year"])
                if request.query_params.get("batch_year")
                else None
            ),
            search=request.query_params.get("search"),
        )
        return Response(s.BasicUserDetailSerializer(users, many=True).data)

    @extend_schema(request=s.BasicUserProfileUpdateSerializer, responses=s.BasicUserDetailSerializer)
    def partial_update(self, request: Any, pk: str | None = None) -> Response:
        try:
            user_id = int(pk or 0)
        except (ValueError, TypeError):
            raise NotFound("Invalid user identifier.")

        user = selectors.users.get_user_by_id(user_id)
        if not user:
            raise NotFound("User not found.")
        self.check_object_permissions(request, user)

        serializer = s.BasicUserProfileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated = user_service.update_basic_user_profile(
                user_id=user_id,
                updates=serializer.validated_data,
                performed_by_id=_get_actor_id(request),
            )
        except domain_exc.DomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": exc.message}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(s.BasicUserDetailSerializer(updated).data)

    @extend_schema(request=s.UserActionReasonSerializer, responses=s.BasicUserDetailSerializer)
    @action(detail=True, methods=["post"])
    def deactivate(self, request: Any, pk: str | None = None) -> Response:
        try:
            user_id = int(pk or 0)
        except (ValueError, TypeError):
            raise NotFound("Invalid user identifier.")

        user = selectors.users.get_user_by_id(user_id)
        if not user:
            raise NotFound("User not found.")
        self.check_object_permissions(request, user)

        serializer = s.UserActionReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated = user_service.deactivate_user(
                user_id=user_id,
                reason=serializer.validated_data["reason"],
                performed_by_id=_get_actor_id(request),
            )
        except domain_exc.DomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": exc.message}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(s.BasicUserDetailSerializer(updated).data)

    @extend_schema(request=s.UserActionReasonSerializer, responses=s.BasicUserDetailSerializer)
    @action(detail=True, methods=["post"])
    def reactivate(self, request: Any, pk: str | None = None) -> Response:
        try:
            user_id = int(pk or 0)
        except (ValueError, TypeError):
            raise NotFound("Invalid user identifier.")

        user = selectors.users.get_user_by_id(user_id)
        if not user:
            raise NotFound("User not found.")
        self.check_object_permissions(request, user)

        serializer = s.UserActionReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            updated = user_service.reactivate_user(
                user_id=user_id,
                reason=serializer.validated_data["reason"],
                performed_by_id=_get_actor_id(request),
            )
        except domain_exc.DomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": exc.message}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(s.BasicUserDetailSerializer(updated).data)

    @extend_schema(request=s.BulkUserCSVUploadSerializer)
    @action(detail=False, methods=["post"])
    def bulk_create(self, request: Any) -> Response:
        serializer = s.BulkUserCSVUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        csv_file = serializer.validated_data["csv_file"]

        try:
            csv_content = csv_file.read().decode("utf-8")
        except UnicodeDecodeError:
            return Response(
                {"error": {"code": "invalid_encoding", "message": "CSV must be UTF-8 encoded."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = user_service.execute_bulk_user_creation(
                csv_content=csv_content, performed_by_id=_get_actor_id(request)
            )
        except domain_exc.BulkLimitExceededError as exc:
            return Response(
                {"error": {"code": exc.code, "message": exc.message}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        status_code = (
            status.HTTP_200_OK
            if result.get("failed_count", 0) == 0
            else status.HTTP_207_MULTI_STATUS
        )
        return Response(result, status=status_code)

    @extend_schema(request=s.BulkStatusUpdateSerializer)
    @action(detail=False, methods=["post"])
    def bulk_status(self, request: Any) -> Response:
        serializer = s.BulkStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            result = user_service.execute_bulk_status_update(
                user_ids=data["user_ids"],
                action=data["action"],
                reason=data["reason"],
                performed_by_id=_get_actor_id(request),
            )
        except domain_exc.BulkLimitExceededError as exc:
            return Response(
                {"error": {"code": exc.code, "message": exc.message}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(result, status=status.HTTP_200_OK)


# ==============================================================================
# 2. ROLE MANAGEMENT VIEWSET (UC-SA-006..011)
# ==============================================================================


class RoleManagementViewSet(viewsets.ViewSet):
    """Role catalog, assignments, handovers, and extensions."""

    permission_classes = [IsSuperAdminPrincipal, EnforceDataIsolationBoundary]

    @extend_schema(responses=s.RoleDefinitionDetailSerializer(many=True))
    @action(detail=False, methods=["get"])
    def definitions(self, request: Any) -> Response:
        category = request.query_params.get("category")
        defs = selectors.roles.list_role_definitions(category=category)
        return Response(s.RoleDefinitionDetailSerializer(defs, many=True).data)

    @extend_schema(responses=s.RoleDefinitionDetailSerializer)
    @action(detail=False, methods=["get"])
    def availability(self, request: Any) -> Response:
        role_code = request.query_params.get("role_code")
        scope = request.query_params.get("scope", "institute")
        if not role_code:
            return Response(
                {"error": {"code": "missing_role_code", "message": "role_code query parameter is required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        avail = selectors.roles.get_role_availability(role_code=role_code, scope=scope)
        return Response(avail)

    @extend_schema(request=s.RoleAssignmentCreateSerializer, responses=s.RoleAssignmentDetailSerializer)
    def create(self, request: Any) -> Response:
        serializer = s.RoleAssignmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        target_user = selectors.users.get_user_by_id(data["target_user_id"])
        if not target_user:
            raise NotFound("Target user not found.")

        role_def = selectors.roles.get_role_definition(data["role_code"])
        if not role_def:
            raise NotFound("Role definition not found.")

        spec = domain_dc.RoleAssignmentSpec(
            role_code=role_def.code,
            target_user_id=target_user.id,
            target_user_kind=target_user.kind,
            start_date=data["start_date"],
            end_date=data.get("end_date"),
            scope=data.get("scope", "institute"),
            reason=data.get("reason", ""),
            is_singular=role_def.is_singular,
            is_time_bound=role_def.is_time_bound,
            allowed_kinds=tuple(role_def.get_allowed_kinds_set()),
        )

        try:
            assignment = role_service.assign_role(
                spec=spec, performed_by_id=_get_actor_id(request)
            )
        except domain_exc.DomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": exc.message}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            s.RoleAssignmentDetailSerializer(assignment).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(request=s.RoleReassignmentSerializer, responses=s.RoleAssignmentDetailSerializer)
    @action(detail=True, methods=["post"])
    def reassign(self, request: Any, pk: str | None = None) -> Response:
        try:
            assignment_id = int(pk or 0)
        except (ValueError, TypeError):
            raise NotFound("Invalid assignment identifier.")

        assignment = RoleAssignment.objects.select_related("role").filter(id=assignment_id).first()
        if not assignment:
            raise NotFound("Role assignment not found.")

        serializer = s.RoleReassignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        new_holder = selectors.users.get_user_by_id(data["new_holder_id"])
        if not new_holder:
            raise NotFound("New role holder not found.")

        spec = domain_dc.RoleReassignmentSpec(
            role_assignment_id=assignment.id,
            role_code=assignment.role.code,
            previous_holder_id=assignment.user_id,
            new_holder_id=new_holder.id,
            new_holder_kind=new_holder.kind,
            effective_date=data["effective_date"],
            handover_tasks=data.get("handover_tasks", True),
            audit_access_days=data.get("audit_access_days", 90),
            reason=data.get("reason", ""),
        )

        try:
            new_assignment = role_service.reassign_role(
                spec=spec, performed_by_id=_get_actor_id(request)
            )
        except domain_exc.DomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": exc.message}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(s.RoleAssignmentDetailSerializer(new_assignment).data)

    @extend_schema(request=s.RoleRevocationSerializer, responses=s.RoleAssignmentDetailSerializer)
    @action(detail=True, methods=["post"])
    def revoke(self, request: Any, pk: str | None = None) -> Response:
        try:
            assignment_id = int(pk or 0)
        except (ValueError, TypeError):
            raise NotFound("Invalid assignment identifier.")

        assignment = RoleAssignment.objects.filter(id=assignment_id).first()
        if not assignment:
            raise NotFound("Role assignment not found.")

        serializer = s.RoleRevocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        spec = domain_dc.RoleRevocationSpec(
            role_assignment_id=assignment_id,
            is_emergency=data.get("is_emergency", False),
            notice_date=data.get("notice_date", timezone.now().date()),
            effective_date=data["effective_date"],
            reason=data["reason"],
            pending_tasks_disposition=data.get("pending_tasks_disposition", "transfer"),
            new_task_holder_id=data.get("new_task_holder_id"),
        )

        try:
            revoked = role_service.revoke_role(
                spec=spec, performed_by_id=_get_actor_id(request)
            )
        except domain_exc.DomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": exc.message}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(s.RoleAssignmentDetailSerializer(revoked).data)

    @extend_schema(request=s.RoleExtensionSerializer, responses=s.RoleAssignmentDetailSerializer)
    @action(detail=True, methods=["post"])
    def extend(self, request: Any, pk: str | None = None) -> Response:
        try:
            assignment_id = int(pk or 0)
        except (ValueError, TypeError):
            raise NotFound("Invalid assignment identifier.")

        assignment = RoleAssignment.objects.filter(id=assignment_id).first()
        if not assignment:
            raise NotFound("Role assignment not found.")

        serializer = s.RoleExtensionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            extended = role_service.extend_role_validity(
                assignment_id=assignment_id,
                new_end_date=data["new_end_date"],
                reason=data["reason"],
                performed_by_id=_get_actor_id(request),
            )
        except domain_exc.DomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": exc.message}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(s.RoleAssignmentDetailSerializer(extended).data)


# ==============================================================================
# 3. ACTIVE ROLE SWITCH VIEW (UC-SA-011)
# ==============================================================================


class ActiveRoleSwitchView(APIView):
    """Allows authenticated multi-role users to switch active operating context."""

    permission_classes = [IsAuthenticated]

    @extend_schema(request=s.ActiveRoleSwitchSerializer)
    def post(self, request: Any) -> Response:
        serializer = s.ActiveRoleSwitchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_role = serializer.validated_data["target_role_code"]
        actor_id = _get_actor_id(request)

        try:
            role_service.switch_active_role(
                user_id=actor_id, target_role_code=target_role
            )
        except domain_exc.DomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": exc.message}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({"status": "switched", "active_role": target_role})


# ==============================================================================
# 4. ARCHIVAL VIEWSET (UC-SA-012..013, ISS-SA-004)
# ==============================================================================


class ArchivalViewSet(viewsets.ViewSet):
    """User archival, reversibility window management, and historical archiving."""

    permission_classes = [
        IsSuperAdminPrincipal,
        RequiresCriticalActionConfirmation,
        EnforceDataIsolationBoundary,
    ]

    @extend_schema(responses=s.ArchivedUserDetailSerializer(many=True))
    @action(detail=False, methods=["get"])
    def users(self, request: Any) -> Response:
        status_filter = request.query_params.get("status")
        records = selectors.archival.list_archived_users(status=status_filter)
        return Response(s.ArchivedUserDetailSerializer(records, many=True).data)

    @extend_schema(request=s.UserActionReasonSerializer, responses=s.ArchivedUserDetailSerializer)
    @action(detail=True, methods=["post"])
    def archive_user(self, request: Any, pk: str | None = None) -> Response:
        try:
            user_id = int(pk or 0)
        except (ValueError, TypeError):
            raise NotFound("Invalid user identifier.")

        serializer = s.UserActionReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            record = archival_service.archive_user(
                user_id=user_id,
                reason=serializer.validated_data["reason"],
                performed_by_id=_get_actor_id(request),
            )
        except domain_exc.DomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": exc.message}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            s.ArchivedUserDetailSerializer(record).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(request=s.UserActionReasonSerializer, responses=s.BasicUserDetailSerializer)
    @action(detail=True, methods=["post"])
    def restore_user(self, request: Any, pk: str | None = None) -> Response:
        try:
            user_id = int(pk or 0)
        except (ValueError, TypeError):
            raise NotFound("Invalid user identifier.")

        serializer = s.UserActionReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            restored = archival_service.restore_archived_user(
                user_id=user_id,
                reason=serializer.validated_data["reason"],
                performed_by_id=_get_actor_id(request),
            )
        except domain_exc.ReversibilityExpiredError as exc:
            return Response(
                {"error": {"code": exc.code, "message": exc.message}},
                status=status.HTTP_409_CONFLICT,
            )
        except domain_exc.DomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": exc.message}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(s.BasicUserDetailSerializer(restored).data)

    @extend_schema(responses=s.HistoricalDataArchiveDetailSerializer(many=True))
    @action(detail=False, methods=["get"])
    def historical(self, request: Any) -> Response:
        cat = request.query_params.get("category")
        archives = selectors.archival.list_historical_archives(category=cat)
        return Response(s.HistoricalDataArchiveDetailSerializer(archives, many=True).data)

    @extend_schema(request=s.HistoricalArchiveCreateSerializer, responses=s.HistoricalDataArchiveDetailSerializer)
    @action(detail=False, methods=["post"])
    def archive_historical(self, request: Any) -> Response:
        serializer = s.HistoricalArchiveCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            archive = archival_service.archive_historical_data(
                category=data["category"],
                date_start=data["date_range_start"],
                date_end=data["date_range_end"],
                record_count=data.get("record_count", 0),
                backup_file_path=data.get("backup_file_path", ""),
                backup_checksum=data.get("backup_checksum", ""),
                retention_years=data.get("retention_years", 5),
                performed_by_id=_get_actor_id(request),
            )
        except domain_exc.DomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": exc.message}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            s.HistoricalDataArchiveDetailSerializer(archive).data,
            status=status.HTTP_201_CREATED,
        )


# ==============================================================================
# 5. PURGE REQUEST VIEWSET (UC-SA-014, BR-SA-022, CW-SA-01)
# ==============================================================================


class PurgeRequestViewSet(viewsets.ViewSet):
    """Dual-authorization permanent purge management.

    Strict separation: Super Admin requests, IT Head authorizes.
    """

    def get_permissions(self) -> list[Any]:
        if self.action == "authorize":
            return [
                IsITHeadPrincipal(),
                RequiresCriticalActionConfirmation(),
                EnforceDataIsolationBoundary(),
            ]
        return [
            IsSuperAdminPrincipal(),
            RequiresCriticalActionConfirmation(),
            EnforceDataIsolationBoundary(),
        ]

    @extend_schema(request=s.PurgeRequestCreateSerializer, responses=s.PurgeRequestDetailSerializer)
    def create(self, request: Any) -> Response:
        serializer = s.PurgeRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            purge_req = purge_service.request_permanent_purge(
                archive_id=data["archive_id"],
                reason=data["reason"],
                super_admin_id=_get_actor_id(request),
            )
        except domain_exc.DomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": exc.message}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            s.PurgeRequestDetailSerializer(purge_req).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(responses=s.PurgeRequestDetailSerializer(many=True))
    def list(self, request: Any) -> Response:
        status_filter = request.query_params.get("status")
        requests = selectors.archival.list_purge_requests(status=status_filter)
        return Response(s.PurgeRequestDetailSerializer(requests, many=True).data)

    @extend_schema(request=s.PurgeAuthorizationDecisionSerializer, responses=s.PurgeRequestDetailSerializer)
    @action(detail=True, methods=["post"])
    def authorize(self, request: Any, pk: str | None = None) -> Response:
        try:
            req_id = int(pk or 0)
        except (ValueError, TypeError):
            raise NotFound("Invalid purge request identifier.")

        serializer = s.PurgeAuthorizationDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            decision_req = purge_service.authorize_permanent_purge(
                request_id=req_id,
                it_head_id=_get_actor_id(request),
                approved=data["approved"],
                comments=data.get("comments", ""),
            )
        except domain_exc.DomainError as exc:
            return Response(
                {"error": {"code": exc.code, "message": exc.message}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(s.PurgeRequestDetailSerializer(decision_req).data)


# ==============================================================================
# 6. AUDIT LOG VIEWSET (UC-SA-015..017)
# ==============================================================================


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """Immutable audit trail queries and safe CSV export."""

    permission_classes = [IsSuperAdminPrincipal, EnforceDataIsolationBoundary]
    queryset = SuperAdminAuditLog.objects.all().order_by("-timestamp")
    serializer_class = s.SuperAdminAuditLogSerializer

    def list(self, request: Any, *args: Any, **kwargs: Any) -> Response:
        actor_user_id = (
            int(request.query_params["actor_user_id"])
            if request.query_params.get("actor_user_id")
            else None
        )
        logs = selectors.audit.query_audit_logs(
            actor_user_id=actor_user_id,
            action=request.query_params.get("action"),
            resource_type=request.query_params.get("resource_type"),
            date_from=(
                timezone.datetime.fromisoformat(request.query_params["date_from"])
                if request.query_params.get("date_from")
                else None
            ),
            date_to=(
                timezone.datetime.fromisoformat(request.query_params["date_to"])
                if request.query_params.get("date_to")
                else None
            ),
        )
        return Response(s.SuperAdminAuditLogSerializer(logs, many=True).data)

    @action(detail=False, methods=["get"])
    def export(self, request: Any) -> HttpResponse:
        filters = {
            "actor_user_id": request.query_params.get("actor_user_id"),
            "action": request.query_params.get("action"),
            "resource_type": request.query_params.get("resource_type"),
        }
        dataset = selectors.audit.generate_audit_report_dataset(filters=filters)
        header = [
            "id",
            "actor_id",
            "action",
            "resource_type",
            "resource_id",
            "ip_address",
            "timestamp",
            "details",
        ]
        rows = (
            [
                item.get("id"),
                item.get("actor_id"),
                item.get("action"),
                item.get("resource_type"),
                item.get("resource_id"),
                item.get("ip_address"),
                item.get("timestamp"),
                str(item.get("details", "")),
            ]
            for item in dataset
        )

        filename = f"system_admin_audit_{timezone.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return csv_utils.stream(filename=filename, header=header, rows=rows)


# ==============================================================================
# 7. DASHBOARD & SYSTEM CONFIG VIEWS (UC-SA-018, UC-SA-023)
# ==============================================================================


class DashboardView(APIView):
    """Aggregate statistics for the Super Admin overview dashboard."""

    permission_classes = [IsSuperAdminPrincipal, EnforceDataIsolationBoundary]

    @extend_schema(responses=s.DashboardMetricsSerializer)
    def get(self, request: Any) -> Response:
        metrics = selectors.dashboard.get_super_admin_dashboard_metrics()
        return Response(metrics)


class SystemConfigView(APIView):
    """Read and update whitelisted global system configuration parameters."""

    permission_classes = [IsSuperAdminPrincipal, EnforceDataIsolationBoundary]

    def get(self, request: Any) -> Response:
        params = selectors.config.get_all_permitted_parameters()
        return Response(params)

    @extend_schema(request=s.SystemParameterUpdateSerializer)
    def patch(self, request: Any, key: str | None = None) -> Response:
        param_key = key or request.data.get("key")
        if not param_key:
            return Response(
                {"error": {"code": "missing_key", "message": "Parameter key is required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = s.SystemParameterUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        value = serializer.validated_data["value"]

        try:
            param = config_service.update_system_parameter(
                key=param_key,
                value=value,
                performed_by_id=_get_actor_id(request),
            )
        except domain_exc.ConfigurationBoundaryViolationError as exc:
            return Response(
                {"error": {"code": exc.code, "message": exc.message}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({
            "key": param.key,
            "value": param.value,
            "description": param.description,
            "data_type": param.data_type,
            "updated_at": param.updated_at,
        })
